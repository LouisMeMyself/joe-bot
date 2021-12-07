import os
from datetime import datetime

from dotenv import load_dotenv
from web3 import exceptions, Web3

from joeBot import Constants, JoeSubGraph
from joeBot.Constants import ZERO_ADDRESS_256

load_dotenv()

# web3
w3 = Web3(Web3.HTTPProvider(Constants.AVAX_RPC))
if not w3.isConnected():
    print("Error web3 can't connect")


class JoeMaker:
    def __init__(self):
        # account
        self.account = w3.eth.account.privateKeyToAccount((os.getenv("PRIVATE_KEY")))

        # contracts
        self.joeMakerV1 = w3.eth.contract(address=Constants.JOEMAKERV1_ADDRESS, abi=Constants.JOEMAKERV1_ABI)
        self.joeMakerV2 = w3.eth.contract(address=Constants.JOEMAKERV2_ADDRESS, abi=Constants.JOEMAKERV2_ABI)
        self.joeMakerV3 = w3.eth.contract(address=Constants.JOEMAKERV3_ADDRESS, abi=Constants.JOEMAKERV3_ABI)

        # version actually used
        self.joeMaker = self.joeMakerV3

    def changeToVersion(self, version):
        if version == "v1":
            self.joeMaker = self.joeMakerV1
        elif version == "v2":
            self.joeMaker = self.joeMakerV2
        elif version == "v3":
            self.joeMaker = self.joeMakerV3
        else:
            raise ValueError
        return "Now using JoeMaker{}".format(version.upper())

    def setBridges(self, tokens, bridges):
        """
        set bridges.
        """
        errors = []
        for token, bridge in zip(map(w3.toChecksumAddress, tokens), map(w3.toChecksumAddress, bridges)):
            set_bridge = self.joeMaker.functions.setBridge(token, bridge)
            try:
                set_bridge.call()
                try:
                    tx_hash = self.execContract(set_bridge)

                    w3.eth.wait_for_transaction_receipt(tx_hash)
                except Exception as e:
                    errors.append("[{}] Error setting bridge:\n{} -> {}: {}".format(
                            datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                            token, bridge, e))
            except Exception as e:
                errors.append("[{}] Error setting bridge locally:\n{} -> {}: {}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                        token, bridge, e))
        return errors

    def execContract(self, func_):
        """
        call contract transactional function func
        """
        nonce = w3.eth.getTransactionCount(self.account.address)
        construct_txn = func_.buildTransaction({'from': self.account.address, 'nonce': nonce})
        signed = self.account.signTransaction(construct_txn)
        tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
        return tx_hash.hex()

    def _callConvertLocally(self, tokens0, tokens1):
        safe_tokens0, safe_tokens1, error_on_pairs = [], [], []
        for token0, token1 in zip(map(Web3.toChecksumAddress, tokens0), map(Web3.toChecksumAddress, tokens1)):
            try:
                self.joeMaker.functions.convert(token0, token1).call({"from": self.account.address})
                safe_tokens0.append(token0)
                safe_tokens1.append(token1)
            except Exception as e:
                error_on_pairs.append(
                    "[{}] Error at convert locally:\n{} - {}: {}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                        token0, token1, e))
        return safe_tokens0, safe_tokens1, error_on_pairs

    def _callConvertMultiple(self, groups_tokens0, groups_tokens1, error_on_pairs):
        pairs, joe_bought_back, = [], []

        pos = "Starts convertMultiple()"
        for group_tokens0, group_tokens1 in zip(groups_tokens0, groups_tokens1):
            call_convert_multiple = self.joeMaker.functions.convertMultiple(group_tokens0, group_tokens1)

            try:
                pos = "Sends convertMultiple()"
                tx_hash = self.execContract(call_convert_multiple)

                pos = "Waits for convertMultiple()"
                transaction_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                pos = "Decodes convertMultiple() receipt"
                pairs, joe_bought_back = decodeTransactionReceipt(
                    transaction_receipt, group_tokens0, group_tokens1, pairs, joe_bought_back)
            except Exception as e:
                error_on_pairs.append(
                    "[{}] Error at {}:\n{}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"), pos, e))
                self._callConvert(group_tokens0, group_tokens1, pairs, joe_bought_back, error_on_pairs)
        return pairs, joe_bought_back, error_on_pairs

    def _callConvert(self, tokens0, tokens1, pairs, joe_bought_back, error_on_pairs):
        pos = "Starts convert()"
        for token0, token1 in zip(tokens0, tokens1):
            call_convert = self.joeMaker.functions.convert(token0, token1)

            try:
                pos = "Sends convert()"
                tx_hash = self.execContract(call_convert)

                pos = "Waits for convert()"
                transaction_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                pos = "Decodes convert() receipt"
                pairs, joe_bought_back = decodeTransactionReceipt(
                    transaction_receipt, token0, token1, pairs, joe_bought_back)
            except Exception as e:
                error_on_pairs.append(
                    "[{}] Error at {}:\n{} - {}: {}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                                                            pos, token0, token1, e))

    def callConvertMultiple(self, min_usd_value):
        # Gets JoeMakerV2 position that are worth more than min_usd_value
        tokens0, tokens1 = JoeSubGraph.getJoeMakerPostitions(min_usd_value, self.joeMaker.address)

        # Gets the list of tokens that are safe to convert, those that doesn't revert locally
        safe_tokens0, safe_tokens1, error_on_pairs = self._callConvertLocally(tokens0, tokens1)

        # Groups tokens by list of 25 to avoid reverting because there isn't enough gas
        groups_tokens0, groups_tokens1 = getGroupsOf(safe_tokens0), getGroupsOf(safe_tokens1)

        # calls ConvertMultiple with the previously grouped tokens
        pairs, joe_bought_back, error_on_pairs = self._callConvertMultiple(groups_tokens0, groups_tokens1, error_on_pairs)

        # return pairs, joe_bought_back, error_on_pairs
        return pairs, joe_bought_back, error_on_pairs


def getGroupsOf(tokens, size=25):
    groups, temp = [], []
    for i, data in enumerate(tokens):
        temp.append(Web3.toChecksumAddress(data))
        if (i + 1) % size == 0:
            groups.append(temp)
            temp = []
    if temp:
        groups.append(temp)
    return groups


# cache
symbolOf = {}

def getSymbolOf(address):
    global symbolOf
    if address not in symbolOf:
        symbolOf[address] = w3.eth.contract(address=address, abi=Constants.ERC20_ABI).functions.symbol().call()
    return symbolOf[address]


def decodeTransactionReceipt(tansaction_receipt, tokens0, tokens1, joe_bought_back, pairs):
    logs = tansaction_receipt["logs"]
    nb_tokens = 0
    for i in range(len(logs)):
        if len(logs[i]["topics"]) > 2 and logs[i]["topics"][2].hex() == ZERO_ADDRESS_256:
            if logs[i - 1]["topics"][1].hex() == ZERO_ADDRESS_256:
                shift = 1
            else:
                shift = 0
            if i > 2:
                joe_bought_back.append(int("0x" + logs[i - shift - 2]["data"][-64:], 16) / 1e18)
            try:
                pairs.append("{} - {}".format(getSymbolOf(tokens0[nb_tokens]), getSymbolOf(tokens1[nb_tokens])))
            except IndexError:
                pairs.append("0x" + logs[i - shift - 1]["topics"][-1].hex()[-40:])
            nb_tokens += 1

    joe_bought_back.append(int("0x" + logs[-1]["data"][-64:], 16) / 1e18)
    return pairs, joe_bought_back

# Only executed if you run main.py
if __name__ == '__main__':
    joeMaker = JoeMaker()
    # joeMaker.changeToVersion("v1")
    # print(joeMaker.callConvertMultiple(10000))
    # print(sum(JoeSubGraph.getJoeMakerPostitions(10000, joeMaker.joeMaker.address, True)[3]))
