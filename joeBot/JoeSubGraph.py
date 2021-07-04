import asyncio
import json, requests
from joeBot import Constants


async def genericQuery(query):
    r = requests.post(Constants.JOE_SG_URL, json={'query': query})
    assert(r.status_code == 200)
    return json.loads(r.text)


async def getJoePrice():
    query = await genericQuery("""{
  token(id: "0x6e84a6216ea6dacc71ee8e6b0a5b7322eebc0fdd") {derivedAVAX}
  bundles {avaxPrice}}""")
    avaxPrice = float(query["data"]["bundles"][0]["avaxPrice"])
    joeDerivedAvax = float(query["data"]["token"]["derivedAVAX"])
    return avaxPrice * joeDerivedAvax

# print(asyncio.run(getJoePrice()))