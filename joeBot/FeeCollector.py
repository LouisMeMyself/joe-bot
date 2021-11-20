import os
from datetime import datetime

from dotenv import load_dotenv
from web3 import exceptions, Web3

from joeBot import Constants, JoeSubGraph
from joeBot.JoeSubGraph import getJoeMakerV2Postitions
from joeBot.beautify_string import readable

load_dotenv()

# web3
w3 = Web3(Web3.HTTPProvider(Constants.AVAX_RPC))
if not w3.isConnected():
    print("Error web3 can't connect")

# account
acct = w3.eth.account.privateKeyToAccount((os.getenv("PRIVATE_KEY")))

# contracts
joeMakerV2 = w3.eth.contract(address=Constants.JOEMAKERV2_ADDRESS, abi=Constants.JOEMAKERV2_ABI)


def exec_contract(acct_, nonce_, func_):
    """
    call contract transactional function func
    """
    construct_txn = func_.buildTransaction({'from': acct_.address, 'nonce': nonce_})
    signed = acct_.signTransaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    return tx_hash.hex()


def callConvert(min_usd_value):
    """
    Call convert on all the pairs that meets the requirements (see getJoeMakerV2Positions for more help).
    If one of the transaction revert because of "execution reverted: SafeERC20: Transfer failed", we
    add it to the blacklist because it's a reflect token, and JoeMakerV2 convert function doesn't handle
    that currently.
    If one of the transaction revert because of another error, we print it with the 2 tokens of the
    pair that was problematic. We don't add them to the blacklist because that could change (like if a
    token is paused, it may change).

    :param min_usd_value: The min USD value to be actually converted.
    """

    joeBoughtBack = {}
    errorOnPairs = []

    # get the tokens0 and tokens1 lists of JoeMakerV2's pair that are worth more than min_usd_value
    pos = "getJoeMakerV2Postitions"
    tokens0, tokens1 = getJoeMakerV2Postitions(min_usd_value)

    for i in range(len(tokens0)):
        token0 = Web3.toChecksumAddress(tokens0[i])
        token1 = Web3.toChecksumAddress(tokens1[i])

        nonce = w3.eth.getTransactionCount(acct.address)
        contract_func = joeMakerV2.functions.convert(token0, token1)

        try:
            pos = "Call convert locally"
            contract_func.call()

            pos = "Send transaction"
            tx_hash = exec_contract(acct, nonce, contract_func)
            pos = "Waits for transaction"
            w3.eth.wait_for_transaction_receipt(tx_hash)

            pos = "Gets pair address and tokens name"
            pairAddress = Web3.toChecksumAddress(
                "0x{}".format((w3.eth.getTransactionReceipt(tx_hash)["logs"][0]["topics"][-2]).hex()[-40:]))
            amountJoe = int(w3.eth.getTransactionReceipt(tx_hash)["logs"][-1]["data"][-64:], 16) / 1e18

            token0Contract = w3.eth.contract(address=token0, abi=Constants.ERC20_ABI)
            token1Contract = w3.eth.contract(address=token1, abi=Constants.ERC20_ABI)

            try:
                pairName = "{} - {}".format(token0Contract.functions.symbol().call(),
                                            token1Contract.functions.symbol().call())
            except:
                pairName = pairAddress

            if pairName in joeBoughtBack:
                joeBoughtBack[pairName + " " + pairAddress] = amountJoe
            else:
                joeBoughtBack[pairName] = amountJoe
        except exceptions.SolidityError as e:
            message = "[{}] Solidity Error at {}:\n{}/{}: {}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                                                                     pos, tokens0[i], tokens1[i], repr(e))
            errorOnPairs.append(message)
        except Exception as e:
            message = "[{}] Error at {}:\n{}/{}: {}".format(datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                                                            pos, tokens0[i], tokens1[i], repr(e))
            errorOnPairs.append(message)

    return joeBoughtBack, errorOnPairs


# Only executed if you run main.py
if __name__ == '__main__':
    print(JoeSubGraph.getAvaxBalance(acct.address))
    print(JoeSubGraph.getJoeMakerV2Postitions(10000))
    print("\n".join(
        ["From {} : {} $JOE".format(pair, readable(amount, 2)) for pair, amount in callConvert(10000)[0].items()]))
