import asyncio
import json, requests
import time

from web3 import Web3
from joeBot import Constants

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)


async def genericExchangeQuery(query):
    r = requests.post(Constants.JOE_EXCHANGE_SG_URL, json={'query': query})
    assert (r.status_code == 200)
    return json.loads(r.text)


async def genericBarQuery(query):
    r = requests.post(Constants.JOE_BAR_SG_URL, json={'query': query})
    assert (r.status_code == 200)
    return json.loads(r.text)


async def getAvaxPrice():
    query = await genericExchangeQuery("{bundles {avaxPrice}}")
    return float(query["data"]["bundles"][0]["avaxPrice"])

async def getJoePrice():
    query = await genericExchangeQuery("""{
  token(id: "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd") {derivedAVAX}}""")
    avaxPrice = await getAvaxPrice()
    joeDerivedAvax = float(query["data"]["token"]["derivedAVAX"])
    return avaxPrice * joeDerivedAvax


async def getTVL():
    queryExchange = await genericExchangeQuery("""{pairs{reserveUSD}}""")
    JoeHeldInJoeBar = float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))
    joePrice = await  getJoePrice()

    sum_ = JoeHeldInJoeBar * joePrice
    for reserveUSD in queryExchange["data"]["pairs"]:
        sum_ += float(reserveUSD["reserveUSD"])
    return sum_


async def getPriceOf(symbol):
    symbol = symbol.lower().replace(" ", "")
    try:
        address = Constants.NAME2ADDRESS[symbol]
    except:
        return "Unknown Token symbol"
    query = await genericExchangeQuery('{token(id: "' + address + '") {derivedAVAX}}')
    avaxPrice = await getAvaxPrice()
    derivedAvax = float(query["data"]["token"]["derivedAVAX"])
    return avaxPrice * derivedAvax, 1/derivedAvax


async def reloadAssets():
    query = await genericExchangeQuery("{tokens{id, symbol, liquidity, derivedAVAX}}")
    temp = {d["symbol"].lower().replace(" ", ""): d["id"] for d in query["data"]["tokens"] if
           float(d["liquidity"]) * float(d["derivedAVAX"]) >= 100}
    dic = {}
    for key, value in temp.items():
        if key[0] == "w" and key[-2:] == ".e":
            dic[key[1:-2]] = value
        elif key[-2:] == ".e":
            dic[key[:-2]] = value
        elif key in dic:
            pass
        else:
            dic[key] = value
    with open("D:/Python_scripts/JoeBot/utils/avaxassets.json", "w") as f:
        json.dump(dic, f)
    Constants.reloadAvaxAssets()


if __name__ == '__main__':
    print(asyncio.run(getJoePrice()))
    print(asyncio.run(getTVL()))
    print(asyncio.run(reloadAssets()))
