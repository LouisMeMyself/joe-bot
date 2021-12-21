import os
from datetime import datetime

from dotenv import load_dotenv
from web3 import Web3

from joeBot import Constants, JoeSubGraph
from joeBot.Constants import ZERO_ADDRESS_256
from joeBot.Utils import readable

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
        gas = int(float(func_.estimateGas({'from': self.account.address})) * (1 + Constants.PREMIUM_PER_TRANSACTION))
        if gas > Constants.MAX_GAS_PER_BLOCK:
            raise Exception("Max gas per block reached")
        construct_txn = func_.buildTransaction({'from': self.account.address, 'nonce': nonce, 'gas': gas})
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
                print(e)
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
        print(tokens0, tokens1)

        # Gets the list of tokens that are safe to convert, those that doesn't revert locally
        safe_tokens0, safe_tokens1, error_on_pairs = self._callConvertLocally(tokens0, tokens1)

        # Groups tokens by list of 25 to avoid reverting because there isn't enough gas
        groups_tokens0, groups_tokens1 = getGroupsOf(safe_tokens0), getGroupsOf(safe_tokens1)

        # return 0, 0, 0
        # calls ConvertMultiple with the previously grouped tokens
        pairs, joe_bought_back, error_on_pairs = self._callConvertMultiple(groups_tokens0, groups_tokens1,
                                                                           error_on_pairs)

        # return pairs, joe_bought_back, error_on_pairs
        return pairs, joe_bought_back, error_on_pairs

    def decodeTxHash(self, tx_hashs):
        tx_hashs = tx_hashs.split()
        joe_bought_back_last7d = JoeSubGraph.getJoeBuyBackLast7d()
        JM_ADDRESS_256 = "0x000000000000000000000000{}".format(self.joeMaker.address[2:].lower())
        nb_tokens, joe_bought_back, pairs = 0, [], []
        for tx_hash in tx_hashs:
            logs = w3.eth.wait_for_transaction_receipt(tx_hash)["logs"]
            for i in range(len(logs)):
                if len(logs[i]["topics"]) > 2:
                    if (logs[i]["topics"][1].hex() == JM_ADDRESS_256
                            and logs[i]["topics"][2].hex() == JM_ADDRESS_256 and len(logs[i]["data"]) == 64 * 2 + 2):
                        pairTokens = [getSymbolOf(token) for token in getPairTokens(logs[i].address)]
                        pairs.append("{} - {}".format(pairTokens[0], pairTokens[1]))
                    if logs[i]["topics"][2].hex() == ZERO_ADDRESS_256:
                        if logs[i - 1]["topics"][1].hex() == ZERO_ADDRESS_256:
                            shift = 1
                        else:
                            shift = 0
                        if i > 2:
                            joe_bought_back.append(int("0x" + logs[i - shift - 2]["data"][-64:], 16) / 1e18)
                        nb_tokens += 1

            joe_bought_back.append(int("0x" + logs[-1]["data"][-64:], 16) / 1e18)

        joe_price = JoeSubGraph.getJoePrice()
        sum_ = sum(joe_bought_back)

        message = ["{} : {} $JOE".format(pair, readable(amount, 2)) for pair, amount in
                   zip(pairs, joe_bought_back)]

        message.append("Total buyback: {} $JOE worth ${}".format(readable(sum_, 2),
                                                                 readable(sum_ * joe_price, 2)))

        message.append("Last 7 days buyback: {} $JOE worth ${}".format(
            readable(joe_bought_back_last7d + sum_, 2),
            readable((joe_bought_back_last7d + sum_) * joe_price, 2)))

        if JoeSubGraph.getJoeBuyBackLast7d(True)[-1] == 0:
            JoeSubGraph.addJoeBuyBackToLast7d(sum_, True)

        return message


def getGroupsOf(tokens, size=20):
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
pairTokens = {}


def getSymbolOf(tokenAddress):
    global symbolOf
    if tokenAddress not in symbolOf:
        symbolOf[tokenAddress] = w3.eth.contract(address=tokenAddress,
                                                 abi=Constants.ERC20_ABI).functions.symbol().call()
    return symbolOf[tokenAddress]


def getPairTokens(pairAddress):
    global pairTokens
    if pairAddress not in pairTokens:
        pair_contract = w3.eth.contract(address=pairAddress, abi=Constants.PAIR_ABI)
        pairTokens[pairAddress] = (pair_contract.functions.token0().call(), pair_contract.functions.token1().call())
    return pairTokens[pairAddress]


def decodeTransactionReceipt(transaction_receipt, tokens0, tokens1, joe_bought_back, pairs):
    logs = transaction_receipt["logs"]
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
    print("\n".join(joeMaker.decodeTxHash("0xb52c9d72aa4862f9310b9eca93ace03216ced0ee9a5009493cfe309de3c6db87 0x1defaa7b2e8e5ea2ed37878ce30ffdaed02920f769e9968f0eb59293f0bc1335 0x81c9746823905676cdbfe8ccc943135e48ae51d551d8875b1b19b0873f3707f9 0x33b0b9d6d53b92acb22579572e7bab59960d135d4104d28e096570a3489b7330 0x2aec7944968bee3c34d66c5d0e13c922012124524756df235ea1d723c69622e1 0xdaa69a6a17760350ca47b81edcd6998e0bbd92951218a288d36b2c570010edf5 0x2f1585cdb6e3582deed34d0c32ff7323d75ff06cf814747814cb79db1b5851d0 0x00c43f125ae79b11d2162710eb9a342f4d52ca66ae21d1c5bc17b06c8f0fd746 0x711c043c369a3763db4f1d6e9768ffaf4f2e8b1a1541703d07e9c304a4c955e2 0x1b4bb2779dcac3189d96efcb693e5d69ed96702e04feb9f0707cf7884a2f93d3 0x3101ff25bdd333508e8db2cc7e749f1ab6bbd9826663a163470f75c04be229b2 0xe9a12bdfb950be5d66a2be807e130750259a0f0142505949cc1849a3cece64c5 0x2b6e22f76b64dba96bb05c5e91d250f0519841a7dd646895a8101244cf0aa5aa")))
    # joeMaker.changeToVersion("v1")
    # print(joeMaker.callConvertMultiple(6000))
    # print(w3.eth.get_transaction_receipt("0xa51a19ae77462e16f4a6aceb8d2d8b938e86ef52c1e0c392df938d36565ad89d"))
    # print(sum(JoeSubGraph.getJoeMakerPostitions(10000, joeMaker.joeMaker.address, True)[3]))
