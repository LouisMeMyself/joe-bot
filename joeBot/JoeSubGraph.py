import asyncio
import json, requests
from joeBot import Constants


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


async def getTVL():
    queryExchange = await genericExchangeQuery("""{pairs{reserveUSD}}""")
    queryBar = await genericBarQuery("""{bars{joeHarvestedUSD}}""")

    sum_ = float(queryBar["data"]["bars"][0]["joeHarvestedUSD"])
    for reserveUSD in queryExchange["data"]["pairs"]:
        sum_ += float(reserveUSD["reserveUSD"])
    return sum_



# print(asyncio.run(getJoePrice()))
# print(asyncio.run(getTVL()))
