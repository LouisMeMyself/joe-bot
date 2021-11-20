import datetime
import json
import time

import pandas as pd
import requests
from web3 import Web3

from joeBot import Constants
from joeBot.Constants import E18
from joeBot.beautify_string import readable, smartRounding

# web3
w3 = Web3(Web3.HTTPProvider(Constants.AVAX_RPC))
if not w3.isConnected():
    print("Error web3 can't connect")

joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI)


def genericQuery(query, sg_url=Constants.JOE_EXCHANGE_SG_URL):
    r = requests.post(sg_url, json={'query': query})
    assert (r.status_code == 200)
    return json.loads(r.text)


def getPriceOf(tokenAddress):
    r = requests.get("https://api.traderjoexyz.com/priceusd/{}".format(tokenAddress))
    assert (r.status_code == 200)
    return json.loads(r.text)


def getDerivedPriceOf(tokenAddress):
    r = requests.get("https://api.traderjoexyz.com/priceavax/{}".format(tokenAddress))
    assert (r.status_code == 200)
    return json.loads(r.text)


def getCirculatingSupply():
    r = requests.get("https://api.traderjoexyz.com/supply/circulating")
    assert (r.status_code == 200)
    return json.loads(r.text)


def getLendingTotalSupply():
    r = requests.get("https://api.traderjoexyz.com/lending/supply")
    assert (r.status_code == 200)
    return json.loads(r.text)


def getLendingTotalBorrow():
    r = requests.get("https://api.traderjoexyz.com/lending/borrow")
    assert (r.status_code == 200)
    return json.loads(r.text)


def getTokenCandles(token_address, period, nb):
    if token_address < Constants.WAVAX_ADDRESS:
        token0, token1 = token_address, Constants.WAVAX_ADDRESS
        isTokenPerAvax = False
    elif token_address > Constants.WAVAX_ADDRESS:
        token0, token1 = Constants.WAVAX_ADDRESS, token_address
        isTokenPerAvax = True
    else:
        # Token is avax
        token0, token1 = Constants.WAVAX_ADDRESS, Constants.USDTe_ADDRESS
        isTokenPerAvax = False

    query = genericQuery('{candles(first:' + nb + ', orderBy: time, orderDirection: desc, \
    where: {token0: "' + token0 + '", token1: "' + token1 + '",\
      period: ' + period + '}) {time, open, high, low, close}}', Constants.JOE_DEXCANDLES_SG_URL)
    query["isTokenPerAvax"] = token0 == Constants.WAVAX_ADDRESS

    data_df = pd.DataFrame(query["data"]["candles"])

    data_df["date"] = data_df["time"].apply(lambda x: datetime.datetime.utcfromtimestamp(x))
    data_df = data_df.set_index('date')

    if not isTokenPerAvax:
        data_df[["open", "close", "high", "low"]] = data_df[["open", "close", "high", "low"]].applymap(
            lambda x: 1 / float(x))
    else:
        data_df[["open", "close", "high", "low"]] = data_df[["open", "close", "high", "low"]].applymap(
            lambda x: float(x))
    return data_df


def getJoeMakerV2Postitions(min_usd_value):
    """
    getJoeMakerPostitions return the position of JoeMaker that are worth more than min_usd_value
    and if he owns less than half the lp.

    :param min_usd_value: The min USD value to be actually returned.
    :return: 2 lists, the first one is the list of the token0 of the pairs that satisfied the requirements
    the second one is the same thing but for token1.
    """
    skip, queryExchange = 0, {}
    tokens0, tokens1 = [], []
    while skip == 0 or len(queryExchange["data"]["liquidityPositions"]) == 1000:
        queryExchange = genericQuery('{liquidityPositions(first: 1000, skip:' + str(skip) +
                                     ' where: {user: "' + Constants.JOEMAKERV2_ADDRESS.lower() + '"}) '
                                     '{liquidityTokenBalance, '
                                     'pair { token0{id}, token1{id}, reserveUSD, totalSupply}}}')
        for liquidityPosition in queryExchange["data"]["liquidityPositions"]:
            pair = liquidityPosition["pair"]

            joeMaker_balance = float(liquidityPosition["liquidityTokenBalance"])
            pair_total_supply = float(pair["totalSupply"])
            pair_reserve_usd = float(pair["reserveUSD"])

            if joeMaker_balance / pair_total_supply * pair_reserve_usd > min_usd_value and \
                    joeMaker_balance / pair_total_supply < 0.49:
                tokens0.append(pair["token0"]["id"])
                tokens1.append(pair["token1"]["id"])
        skip += 1000
    return tokens0, tokens1


# Using API
def getAvaxPrice():
    return getPriceOf(Constants.WAVAX_ADDRESS) / E18


def getAvaxBalance(address):
    return round(float(w3.eth.getBalance(w3.toChecksumAddress(address))) / 1e18, 3)

# Using API
def getJoePrice():
    return getPriceOf(Constants.JOETOKEN_ADDRESS) / E18


def getTVL():
    JoeHeldInJoeBar = float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))
    joePrice = float(getJoePrice())

    sum_ = JoeHeldInJoeBar * joePrice

    skip, queryExchange = 0, {}
    while skip == 0 or len(queryExchange["data"]["pairs"]) == 1000:
        queryExchange = genericQuery("{pairs(first: 1000, skip: " + str(skip) + "){reserveUSD}}")
        for reserveUSD in queryExchange["data"]["pairs"]:
            sum_ += float(reserveUSD["reserveUSD"])
        skip += 1000
    return sum_


# Using API
def getPricesOf(tokenAddress):
    tokenAddress = tokenAddress.lower().replace(" ", "")
    try:
        tokenAddress = Web3.toChecksumAddress(Constants.NAME2ADDRESS[tokenAddress])
    except:
        pass

    try:
        derivedPrice = getDerivedPriceOf(tokenAddress)
    except:
        return "Error: Given address " + tokenAddress + " is not a valid Ethereum address or a valid symbol."

    dPrice = int(derivedPrice) / E18
    avaxPrice = getAvaxPrice()
    return dPrice, (dPrice * avaxPrice)


def reloadAssets():
    skip, queryExchange, tempdic = 0, {}, {}
    while skip == 0 or len(queryExchange["data"]["tokens"]) == 1000:
        queryExchange = genericQuery(
            "{tokens(first: 1000, skip: " + str(skip) + "){id, symbol, liquidity, derivedAVAX}}")
        for d in queryExchange["data"]["tokens"]:
            if float(d["liquidity"]) * float(d["derivedAVAX"]) >= 100:
                tempdic[d["symbol"].lower().replace(" ", "")] = d["id"]
        skip += 1000

    name2address = {}
    for key, value in tempdic.items():
        if key[0] == "w" and key[-2:] == ".e":
            name2address[key[1:-2]] = value
        elif key[-2:] == ".e":
            name2address[key[:-2]] = value
        elif key in name2address:
            pass
        else:
            name2address[key] = value
    Constants.NAME2ADDRESS = name2address


def getJoeBuyBackLast7d():
    now = datetime.datetime.utcnow()
    lastweektimestamp = str(int((now - datetime.timedelta(days=6, hours=12)).timestamp()))
    query = genericQuery('{servings(orderBy: timestamp, orderDirection: desc, first: 1000, where: {timestamp_gt: "' +
                         lastweektimestamp + '"}) {joeServed}}', Constants.JOE_MAKERV2_SG_URL)

    joeServed = 0
    for joeServ in query["data"]["servings"]:
        joeServed += float(joeServ["joeServed"])
    return joeServed


def getAbout():
    joePrice = getJoePrice()
    avaxPrice = getAvaxPrice()
    csupply = float(getCirculatingSupply() / E18)
    mktcap = joePrice * csupply
    farm_tvl = getTVL()
    lending_tvl = float(getLendingTotalSupply() / E18)

    return "$JOE: ${}\n" \
           "$AVAX: ${}\n" \
           "Market Cap: ${}\n" \
           "Circ. Supply: {}\n" \
           "Farm TVL: ${}\n" \
           "Lending TVL: ${}\n" \
           "Total TVL: ${}\n".format(readable(joePrice, 4), smartRounding(avaxPrice), smartRounding(mktcap),
                                     smartRounding(csupply), smartRounding(farm_tvl), smartRounding(lending_tvl),
                                     smartRounding(lending_tvl + farm_tvl))


def avg7d(timestamp):
    query = genericQuery('{candles(where: {\
      token0: "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd",\
      token1: "0xc7198437980c041c805a1edcba50c1ce5db95118",\
      period: 14400,\
      time_lte: ' + timestamp + '},orderBy: time,orderDirection: desc,first: 42) \
      {close, time}}', Constants.JOE_DEXCANDLES_SG_URL)
    closes = query["data"]["candles"]
    if len(closes) == 0:
        return -1
    print(query)
    return sum([1 / float(i["close"]) for i in closes]) / len(closes)


def getLendingAbout():
    lending_tvl = float(getLendingTotalSupply() / E18)
    totalBorrow = float(getLendingTotalBorrow() / E18)

    return "Lending informations:\n" \
           "Total Deposited: ${}\n" \
           "Total Borrowed: ${}\n".format(smartRounding(lending_tvl), smartRounding(totalBorrow))


if __name__ == "__main__":
    # print(getAbout())
    # print(getLendingAbout())
    # print(getJoeBuyBackLast7d())
    print(getJoeMakerV2Postitions(10000))
    print("Done")
