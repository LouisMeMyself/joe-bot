import os
from datetime import datetime
from time import time

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

from joeBot import Constants, JoeSubGraph
from joeBot.Utils import readable

load_dotenv()

# web3
w3 = Web3(Web3.HTTPProvider(Constants.AVAX_RPC))
if not w3.isConnected():
    print("Error web3 can't connect")
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# cache
symbolOf = {}


class MoneyMaker:
    def __init__(self):
        # account
        self.account = w3.eth.account.privateKeyToAccount((os.getenv("PRIVATE_KEY")))

        # contracts
        self.moneyMaker = w3.eth.contract(
            address=Constants.MONEYMAKER_ADDRESS, abi=Constants.MONEYMAKER_ABI
        )

    def setBridges(self, tokens, bridges):
        """
        set bridges
        """
        errors = []
        for token, bridge in zip(
            map(w3.toChecksumAddress, tokens), map(w3.toChecksumAddress, bridges)
        ):
            set_bridge = self.moneyMaker.functions.setBridge(token, bridge)
            try:
                set_bridge.call()
                try:
                    tx_hash = self.execContract(set_bridge)

                    w3.eth.wait_for_transaction_receipt(tx_hash)
                except Exception as e:
                    errors.append(
                        "[{}] Error setting bridge:\n{} -> {}: {}".format(
                            datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                            token,
                            bridge,
                            e,
                        )
                    )
            except Exception as e:
                errors.append(
                    "[{}] Error setting bridge locally:\n{} -> {}: {}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                        token,
                        bridge,
                        e,
                    )
                )
        return errors

    def execContract(self, func_):
        """
        call contract transactional function func
        """
        nonce = w3.eth.get_transaction_count(self.account.address)
        construct_txn = func_.buildTransaction(
            {"from": self.account.address, "nonce": nonce}
        )
        signed = self.account.signTransaction(construct_txn)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def _callConvertLocally(self, tokens0, tokens1, slippage):
        """
        call convert locally to prevent reverts
        """
        safe_tokens0, safe_tokens1, error_on_pairs = [], [], []
        for token0, token1 in zip(
            map(Web3.toChecksumAddress, tokens0), map(Web3.toChecksumAddress, tokens1)
        ):
            try:
                self.moneyMaker.functions.convert(token0, token1, slippage).call(
                    {"from": self.account.address}
                )
                safe_tokens0.append(token0)
                safe_tokens1.append(token1)
            except Exception as e:
                print(e)
                error_on_pairs.append(
                    "[{}] Error at convert locally:\n{} - {}: {}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
                        token0,
                        token1,
                        e,
                    )
                )
        return safe_tokens0, safe_tokens1, error_on_pairs

    def _callConvertMultiple(
        self, groups_tokens0, groups_tokens1, slippage, error_on_pairs
    ):
        """
        call convert on a group of token
        """
        for group_tokens0, group_tokens1 in zip(groups_tokens0, groups_tokens1):
            call_convert_multiple = self.moneyMaker.functions.convertMultiple(
                group_tokens0, group_tokens1, slippage
            )
            try:
                pos = "Sends convertMultiple()"
                tx_hash = self.execContract(call_convert_multiple)

                pos = "Waits for convertMultiple()"
                transaction_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                block_number = transaction_receipt["blockNumber"]
            except Exception as e:
                error_on_pairs.append(
                    "[{}] Error at {}:\n{}".format(
                        datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"), pos, e
                    )
                )
        return error_on_pairs

    def callConvertMultiple(self, min_usd_value, slippage):
        """
        call convert on all LP position that are worth more than `min_usd_value` and with a max slippage of `slippage` (in BP, per 10_000, so 500 is 5%)
        """
        # Gets MoneyMaker position that are worth more than min_usd_value
        tokens0, tokens1 = JoeSubGraph.getMoneyMakerPostitions(
            min_usd_value, self.moneyMaker.address
        )

        # Gets the list of tokens that are safe to convert, those that doesn't revert locally
        safe_tokens0, safe_tokens1, error_on_pairs = self._callConvertLocally(
            tokens0, tokens1, slippage
        )

        # Groups tokens by list of 25 to avoid reverting because there isn't enough gas
        groups_tokens0, groups_tokens1 = (
            getGroupsOf(safe_tokens0),
            getGroupsOf(safe_tokens1),
        )

        # return 0, 0, 0
        # calls ConvertMultiple with the previously grouped tokens
        error_on_pairs = self._callConvertMultiple(
            groups_tokens0, groups_tokens1, slippage, error_on_pairs
        )

        # return from_block, to_block, error_on_pairs
        return error_on_pairs

    def getDailyData(self):
        """
        get daily data of moneyMaker
        """
        now = time()
        # Today at 12pm
        if now % 86400 >= 43200:
            timestamp = now - now % 43200
        # Yesterday at 12pm
        else:
            timestamp = now - now % 86400 - 43200
        to_block = w3.eth.get_block_number()
        from_block = binary_search(9_000_000, to_block, timestamp)

        events = self.getLogConvertEvents(from_block, to_block)
        token = self.getERC20(self.moneyMaker.functions.tokenTo().call())
        precision = 10 ** int(token.functions.decimals().call())
        tokenSymbol = token.functions.symbol().call()

        pairs, amountsSent = [], []
        for event in events:
            args = event["args"]
            pairs.append(
                "{} - {}".format(
                    getSymbolOf(args["token0"]), getSymbolOf(args["token1"])
                )
            )
            amountsSent.append(int(args["amountTOKEN"]) / precision)
        return pairs, amountsSent, tokenSymbol

    def getERC20(self, address):
        """
        return the ERC20 contract of address
        """
        return w3.eth.contract(address=address, abi=Constants.ERC20_ABI)

    def getDailyInfo(self):
        """
        Return today's info, in a list to be sent in different messages if they are too long
        """
        pairs, amounts, symbol = self.getDailyData()

        token_sent_last_7_days = JoeSubGraph.getBuyBackLast7d()
        sum_ = sum(amounts)

        message = [
            "{} : {} ${}".format(pair, readable(amount, 2), symbol)
            for pair, amount in zip(pairs, amounts)
        ]

        message.append("Total: {} ${}".format(readable(sum_, 2), symbol))

        message.append(
            "Last 7 days: {} ${} ".format(
                readable(token_sent_last_7_days + sum_, 2),
                symbol,
            )
        )

        JoeSubGraph.addBuyBackLast7d(sum_, True)

        return message

    def getLogConvertEvents(self, from_block, to_block):
        """
        get all events between `from_block` and `to_block`
        """
        events = self.moneyMaker.events.LogConvert.createFilter(
            fromBlock=from_block, toBlock=to_block
        )
        return events.get_all_entries()


def getGroupsOf(tokens, size=20):
    """
    split a list into groups
    """
    groups, temp = [], []
    for i, data in enumerate(tokens):
        temp.append(Web3.toChecksumAddress(data))
        if (i + 1) % size == 0:
            groups.append(temp)
            temp = []
    if temp:
        groups.append(temp)
    return groups


def getSymbolOf(tokenAddress):
    """
    get the symbol of an address
    """
    global symbolOf
    if tokenAddress not in symbolOf:
        symbolOf[tokenAddress] = (
            w3.eth.contract(address=tokenAddress, abi=Constants.ERC20_ABI)
            .functions.symbol()
            .call()
        )
    return symbolOf[tokenAddress]


def binary_search(from_block, to_block, timestamp):
    """
    binary search to find a block close to the selected timestamp
    """
    if to_block == 0:
        to_block = w3.eth.get_block_number()
    assert (
        w3.eth.get_block(from_block).timestamp
        < timestamp
        < w3.eth.get_block(to_block).timestamp
    ), "timestamp isn't between those 2 blocks"

    while from_block < to_block - 10:
        mid = (from_block + to_block) // 2

        if w3.eth.get_block(mid).timestamp < timestamp:
            from_block = mid
        else:
            to_block = mid
    return from_block


# Only executed if you run main.py
if __name__ == "__main__":
    moneyMaker = MoneyMaker()
    print(moneyMaker.getDailyInfo())
    print(JoeSubGraph.getMoneyMakerPostitions(10_000, return_reserve_and_balance=True))
    # print(moneyMaker.getMoneyMakerMessage(11385055, 11385055))
    # print(
    #     moneyMaker.decodeTxHash(
    #         "0x9c97b375da42d916c0da6f190427492e9f772779576b223173975682a983e5f4"
    #     )
    # )
    # print(JoeSubGraph.getMoneyMakerPostitions(0))
    # moneyMaker.changeToVersion("v1")
    # print(moneyMaker.callConvertMultiple(0, 50))
    # print(w3.eth.get_transaction_receipt("0xa51a19ae77462e16f4a6aceb8d2d8b938e86ef52c1e0c392df938d36565ad89d"))
    # print(sum(JoeSubGraph.getMoneyMakerPostitions(10000, moneyMaker.moneyMaker.address, True)[3]))
