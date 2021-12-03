import os
from datetime import datetime

from dotenv import load_dotenv
from web3 import exceptions, Web3

from joeBot import Constants, JoeSubGraph
from joeBot.Constants import ZERO_ADDRESS_256
from joeBot.JoeSubGraph import getJoeMakerV2Postitions
from joeBot.Utils import readable

load_dotenv()

# web3
w3 = Web3(Web3.HTTPProvider(Constants.AVAX_RPC))
if not w3.isConnected():
    print("Error web3 can't connect")

# account
acct = w3.eth.account.privateKeyToAccount((os.getenv("PRIVATE_KEY")))

# contracts
joeMakerV2 = w3.eth.contract(address=Constants.JOEMAKERV2_ADDRESS, abi=Constants.JOEMAKERV2_ABI)

# cache
symbolOf = {}


def exec_contract(acct_, nonce_, func_):
    """
    call contract transactional function func
    """
    construct_txn = func_.buildTransaction({'from': acct_.address, 'nonce': nonce_})
    signed = acct_.signTransaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    return tx_hash.hex()


def getSymbolOf(address):
    global symbolOf
    if address not in symbolOf:
        symbolOf[address] = w3.eth.contract(address=address, abi=Constants.ERC20_ABI).functions.symbol().call()
    return symbolOf[address]


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


def decodeTransactionReceipt(tansaction_receipt, tokens0, tokens1, joe_bought_back, pairs):
    logs = tansaction_receipt["logs"]
    nb_tokens = 0
    for i in range(len(logs)):
        if len(logs[i]["topics"]) < 3:
            continue
        if logs[i]["topics"][2].hex() == ZERO_ADDRESS_256:
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


def _callConvertLocally(tokens0, tokens1):
    safe_tokens0, safe_tokens1, error_on_pairs = [], [], []
    for token0, token1 in zip(map(Web3.toChecksumAddress, tokens0), map(Web3.toChecksumAddress, tokens1)):
        try:
            joeMakerV2.functions.convert(token0, token1).call()
            safe_tokens0.append(token0)
            safe_tokens1.append(token1)
        except Exception as e:
            error_on_pairs.append(
                "[{}] Error at convert Locally:\n{} - {}: {}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                                                                     token0, token1, e))
    return safe_tokens0, safe_tokens1, error_on_pairs


def _callConvertMultiple(groups_tokens0, groups_tokens1, error_on_pairs):
    pairs, joe_bought_back, = [], []

    pos = "Iterating through groups"
    for group_tokens0, group_tokens1 in zip(groups_tokens0, groups_tokens1):
        nonce = w3.eth.getTransactionCount(acct.address)
        call_convert_multiple = joeMakerV2.functions.convertMultiple(group_tokens0, group_tokens1)

        try:
            pos = "Sends convertMultiple()"
            tx_hash = exec_contract(acct, nonce, call_convert_multiple)

            pos = "Waits for convertMultiple()"
            transaction_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            pos = "Decodes convertMultiple() receipt"
            pairs, joe_bought_back = decodeTransactionReceipt(
                transaction_receipt, group_tokens0, group_tokens1, pairs, joe_bought_back)
        except Exception as e:
            if e is exceptions.SolidityError:
                error_on_pairs.append(
                    "[{}] Solidity Error at {}:\n{}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"), pos, e))
            error_on_pairs.append(
                "[{}] Error on convertMultiple at {}:\n{}".format(
                    datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"), pos, e))
            _callConvert(group_tokens0, group_tokens1, pairs, joe_bought_back, error_on_pairs)
    return pairs, joe_bought_back, error_on_pairs


def _callConvert(tokens0, tokens1, pairs, joe_bought_back, error_on_pairs):
    pos = "Iterating through tokens"
    for token0, token1 in zip(tokens0, tokens1):
        nonce = w3.eth.getTransactionCount(acct.address)
        call_convert = joeMakerV2.functions.convert(token0, token1)

        try:
            pos = "Sends convert()"
            tx_hash = exec_contract(acct, nonce, call_convert)

            pos = "Waits for convert()"
            transaction_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            pos = "Decodes convert() receipt"
            pairs, joe_bought_back = decodeTransactionReceipt(
                transaction_receipt, token0, token1, pairs, joe_bought_back)
        except Exception as e:
            error_on_pairs.append(
                "[{}] Error at {}:\n{} - {}: {}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                                                        pos, token0, token1, e))


def callConvertMultiple(min_usd_value):
    # Gets JoeMakerV2 position that are worth more than min_usd_value
    tokens0, tokens1 = JoeSubGraph.getJoeMakerV2Postitions(min_usd_value)

    # Gets the list of tokens that are safe to convert, those that doesn't revert locally
    safe_tokens0, safe_tokens1, error_on_pairs = _callConvertLocally(tokens0, tokens1)

    # Groups tokens by list of 25 to avoid reverting because there isn't enough gas
    groups_tokens0, groups_tokens1 = getGroupsOf(safe_tokens0), getGroupsOf(safe_tokens1)

    # calls ConvertMultiple with the previously grouped tokens
    pairs, joe_bought_back, error_on_pairs = _callConvertMultiple(groups_tokens0, groups_tokens1, error_on_pairs)

    return pairs, joe_bought_back, error_on_pairs


# Only executed if you run main.py
if __name__ == '__main__':
    print(JoeSubGraph.getAvaxBalance(acct.address))
    print(JoeSubGraph.getJoeMakerV2Postitions(10000))
    # print(callConvertMultiple(10000))
    # print(decodeTransactionReceipt( w3.eth.get_transaction_receipt(
    # "0x0161a740d7548ec79f4d68ee68a01677ed4054bc06037e7ef4ffe2fe4fed6da6"), [], [], [], []))
