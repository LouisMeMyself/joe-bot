import asyncio
import datetime
import json

import pandas as pd
import requests
from web3 import Web3

from joeBot import Constants, JoeContract
# web3
from joeBot.beautify_string import readable, human_format

w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.ERC20_ABI)


async def genericExchangeQuery(query, sg_url=Constants.JOE_EXCHANGE_SG_URL):
    r = requests.post(sg_url, json={'query': query})
    assert (r.status_code == 200)
    return json.loads(r.text)


async def getTokenCandles(token_address, period, nb):
    if token_address < Constants.WAVAX_ADDRESS:
        token0, token1 = token_address, Constants.WAVAX_ADDRESS
        isTokenPerAvax = False
    elif token_address > Constants.WAVAX_ADDRESS:
        token0, token1 = Constants.WAVAX_ADDRESS, token_address
        isTokenPerAvax = True
    else:
        token0, token1 = Constants.WAVAX_ADDRESS, Constants.USDTe_ADDRESS
        isTokenPerAvax = False

    query = await genericExchangeQuery('{candles(first:' + nb + ', orderBy: time, orderDirection: desc, \
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


# # Using subgraph
# async def getAvaxPrice():
#     query = await genericExchangeQuery("{bundles {avaxPrice}}")
#     return float(query["data"]["bundles"][0]["avaxPrice"])


# Using contracts reserve directly
async def getAvaxPrice():
    return JoeContract.getAvaxPrice()


# Using contracts reserve directly
async def getJoePrice():
    return JoeContract.getJoePrice()


# # Using contracts reserve directly
# async def getJoePrice():
#   query = await genericExchangeQuery("""{
# token(id: "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd") {derivedAVAX}}""")
#   avaxPrice = await getAvaxPrice()
#   joeDerivedAvax = float(query["data"]["token"]["derivedAVAX"])
#   return avaxPrice * joeDerivedAvax


async def getTVL():
    JoeHeldInJoeBar = float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))
    joePrice = await getJoePrice()

    sum_ = JoeHeldInJoeBar * joePrice

    skip, queryExchange = 0, {}
    while skip == 0 or len(queryExchange["data"]["pairs"]) == 1000:
        queryExchange = await genericExchangeQuery("{pairs(first: 1000, skip: " + str(skip) + "){reserveUSD}}")
        for reserveUSD in queryExchange["data"]["pairs"]:
            sum_ += float(reserveUSD["reserveUSD"])
        skip += 1000
    return sum_


# Using subgraph
async def getPriceOf(symbol):
    prices = JoeContract.getPriceAndDerivedPriceOfToken(symbol)
    return prices


# # Using subgraph
# async def getPriceOf(symbol):
#     symbol = symbol.lower().replace(" ", "")
#     try:
#         address = Constants.NAME2ADDRESS[symbol]
#     except:
#         return "Unknown Token Symbol"
#     query = await genericExchangeQuery('{token(id: "' + address + '") {derivedAVAX}}')
#     avaxPrice = await getAvaxPrice()
#     derivedAvax = float(query["data"]["token"]["derivedAVAX"])
#     return avaxPrice * derivedAvax, 1 / derivedAvax


async def reloadAssets():
    skip, queryExchange, tempdic = 0, {}, {}
    while skip == 0 or len(queryExchange["data"]["tokens"]) == 1000:
        queryExchange = await genericExchangeQuery(
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


async def getAbout():
    joePrice = await getJoePrice()
    avaxPrice = await getAvaxPrice()
    tsupply = float(w3.fromWei(joetoken_contract.functions.totalSupply().call(), 'ether'))
    develeopmentFunds = float(
        w3.fromWei(joetoken_contract.functions.balanceOf("0xaFF90532E2937fF290009521e7e120ed062d4F34").call(), 'ether'))
    foundationFunds = float(
        w3.fromWei(joetoken_contract.functions.balanceOf("0x66Fb02746d72bC640643FdBa3aEFE9C126f0AA4f").call(), 'ether'))
    strategicInvestorFunds = float(
        w3.fromWei(joetoken_contract.functions.balanceOf("0xc13B1C927565C5AF8fcaF9eF7387172c447f6796").call(), 'ether'))
    csupply = tsupply - develeopmentFunds - foundationFunds - strategicInvestorFunds
    mktcap = joePrice * csupply
    tvl = await getTVL()
    return "$JOE: ${}\n" \
           "$AVAX: ${}\n" \
           "Market Cap: ${}\n" \
           "Circ. Supply: {}\n" \
           "TVL: ${}".format(readable(joePrice, 4), human_format(avaxPrice), human_format(mktcap),
                             human_format(csupply), human_format(tvl))


if __name__ == '__main__':
    # print(asyncio.run(getJoePrice()))
    # print(asyncio.run(getTVL()))
    # print(asyncio.run(getAbout()))
    asyncio.run(reloadAssets())
    print(getPriceOf("snob"))
    # print(Constants.NAME2ADDRESS)
    # print(asyncio.run(getTokenCandles("0x6e84a6216eA6dACC71eE8E6b0a5B7322EEbC0fDd", "3600", "24")))
