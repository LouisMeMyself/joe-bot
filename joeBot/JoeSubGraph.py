import asyncio
import json, requests

from web3 import Web3
from joeBot import Constants

# web3
w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)

async def genericExchangeQuery(query):
    r = requests.post(Constants.JOE_EXCHANGE_SG_URL, json={'query': query})
    assert(r.status_code == 200)
    return json.loads(r.text)

async def genericBarQuery(query):
    r = requests.post(Constants.JOE_BAR_SG_URL, json={'query': query})
    assert(r.status_code == 200)
    return json.loads(r.text)


async def getJoePrice():
    query = await genericExchangeQuery("""{
  token(id: "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd") {derivedAVAX}
  bundles {avaxPrice}}""")
    avaxPrice = float(query["data"]["bundles"][0]["avaxPrice"])
    joeDerivedAvax = float(query["data"]["token"]["derivedAVAX"])
    return avaxPrice * joeDerivedAvax

import numpy as np

async def getTVL():
    queryExchange = await genericExchangeQuery("""{pairs{reserveUSD}}""")
    JoeHeldInJoeBar = float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))
    joePrice = await  getJoePrice()

    sum_ = JoeHeldInJoeBar * joePrice
    for reserveUSD in queryExchange["data"]["pairs"]:
        sum_ += float(reserveUSD["reserveUSD"])
    return sum_


if __name__ == '__main__':
    print(asyncio.run(getJoePrice()))
    print(asyncio.run(getTVL()))