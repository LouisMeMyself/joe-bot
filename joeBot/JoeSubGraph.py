import asyncio
import json, requests

from web3 import Web3
from joeBot import Constants

# web3
from joeBot.beautify_string import readable, human_format

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
    JoeHeldInJoeBar = float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))
    joePrice = await  getJoePrice()

    sum_ = JoeHeldInJoeBar * joePrice

    skip, queryExchange = 0, {}
    while skip == 0 or len(queryExchange["data"]["pairs"]) == 1000:
        queryExchange = await genericExchangeQuery("{pairs(first: 1000, skip: " + str(skip) +"){reserveUSD}}")
        for reserveUSD in queryExchange["data"]["pairs"]:
            sum_ += float(reserveUSD["reserveUSD"])
        skip += 1000
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
    return avaxPrice * derivedAvax, 1 / derivedAvax


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
    Constants.NAME2ADDRESS = dic


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
    print(asyncio.run(getJoePrice()))
    print(asyncio.run(getTVL()))
    print(asyncio.run(getAbout()))

dic = {
    "data": {
        "pairs": [
            {
                "reserveUSD": "1200914.266428902089193887204067439",
                "token0": {
                    "symbol": "VSO"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.00149563633204919149399530174748397",
                "token0": {
                    "symbol": "GRT.e"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.05674812207219700890977883366804041",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "KP3R.e"
                }
            },
            {
                "reserveUSD": "2.666698451777827314995210102638242",
                "token0": {
                    "symbol": "Ragehoge"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1779.180870428097365501582010966075",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "DAI"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "AVME"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "XAVA"
                }
            },
            {
                "reserveUSD": "0.07842943600601349116382692565851716",
                "token0": {
                    "symbol": "xBTC"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.08055430181596570436058796885161027",
                "token0": {
                    "symbol": "BTW"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1.743905878829329558127827875523171",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "xYFI"
                }
            },
            {
                "reserveUSD": "107.7927214043478117492084719304625",
                "token0": {
                    "symbol": "RRTEST"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "2338.408840839645314952695045268663",
                "token0": {
                    "symbol": "CORGI"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1.181296922452749897332038122301889",
                "token0": {
                    "symbol": "xJOE"
                },
                "token1": {
                    "symbol": "JOE"
                }
            },
            {
                "reserveUSD": "2587.459121205724717624938438955072",
                "token0": {
                    "symbol": "COBIE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.2941260942841854970476546542841429",
                "token0": {
                    "symbol": "Nftart"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "6234347.997503683665611210475460224",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "USDT.e"
                }
            },
            {
                "reserveUSD": "2.161320256116367873431638075877499",
                "token0": {
                    "symbol": "TZAP"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "10.23987158053479191041578015732045",
                "token0": {
                    "symbol": "AVAMOON"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.0000000000000001025643910948393050105064771354931",
                "token0": {
                    "symbol": "AVAMOON"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "6079.356001156611176909137438808493",
                "token0": {
                    "symbol": "QI"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.0000000000000322500151837332358958032463853641",
                "token0": {
                    "symbol": "shit"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "39148.59274588862840710345472084253",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "USDT"
                }
            },
            {
                "reserveUSD": "619.3434035611629071620132898534494",
                "token0": {
                    "symbol": "SLED"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "69.63565664134050528508823399996182",
                "token0": {
                    "symbol": "XSafeMoon"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "6.189041821420268851960474598369481",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "VSO"
                }
            },
            {
                "reserveUSD": "10.52648069301855161027450520434686",
                "token0": {
                    "symbol": "TMP"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.6106594441138816394126137321458451",
                "token0": {
                    "symbol": "XFEG"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.00000000000006628520782668425332820944484406323",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "DALTON"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.002341986148353583638661166598877716",
                "token0": {
                    "symbol": "HAT"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "21.51239866504891817437740345105189",
                "token0": {
                    "symbol": "LINK"
                },
                "token1": {
                    "symbol": "USDT"
                }
            },
            {
                "reserveUSD": "2547753.7296633386492136505405623",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1.177851257203933954449039771701706",
                "token0": {
                    "symbol": "HAT"
                },
                "token1": {
                    "symbol": "JOE"
                }
            },
            {
                "reserveUSD": "228651.1986127235959810611709051001",
                "token0": {
                    "symbol": "RELAY"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "191.2665584137483484486119873632944",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "DAI"
                }
            },
            {
                "reserveUSD": "24068145.55630853160986587602457113",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "181.5880667263531460126506021374597",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "QI"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "DAI"
                }
            },
            {
                "reserveUSD": "11.21591226047346101371681166111496",
                "token0": {
                    "symbol": "NAKAMOTO"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "16641.65187735515972069460242252954",
                "token0": {
                    "symbol": "HAT"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "2.16511516174241072026461973024342",
                "token0": {
                    "symbol": "BonfireAVA"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "248.0987564440939513516849846553845",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "SNOB"
                }
            },
            {
                "reserveUSD": "35885.56199254853129399058537850041",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "NEKO"
                }
            },
            {
                "reserveUSD": "0.03125076095081308042755838473556283",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "BabyAvax"
                }
            },
            {
                "reserveUSD": "14.50602350101439409137883811953509",
                "token0": {
                    "symbol": "TMP"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "47.75978776448118047184187034871017",
                "token0": {
                    "symbol": "YAK"
                },
                "token1": {
                    "symbol": "JOE"
                }
            },
            {
                "reserveUSD": "4927.790463024150774810289900111681",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "AntiVax"
                }
            },
            {
                "reserveUSD": "0.9063659688687906402775100297387042",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "XCAT"
                }
            },
            {
                "reserveUSD": "0.9256400108161103461035877078666636",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "KILOO"
                }
            },
            {
                "reserveUSD": "1461.068179540222810268906047400093",
                "token0": {
                    "symbol": "USDT.e"
                },
                "token1": {
                    "symbol": "ZABU"
                }
            },
            {
                "reserveUSD": "2190706.05920709913617209661844681",
                "token0": {
                    "symbol": "LINK.e"
                },
                "token1": {
                    "symbol": "USDT.e"
                }
            },
            {
                "reserveUSD": "10.16898227362406573281857478811638",
                "token0": {
                    "symbol": "SL3"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "934.1134542589580425523510363433433",
                "token0": {
                    "symbol": "LYD"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.002344707130824896721279189439106115",
                "token0": {
                    "symbol": "xJOE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "12929926.11121111896794558642867649",
                "token0": {
                    "symbol": "USDC.e"
                },
                "token1": {
                    "symbol": "DAI.e"
                }
            },
            {
                "reserveUSD": "8826.715990525141526672288594419399",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "USDC.e"
                }
            },
            {
                "reserveUSD": "15193.62486569148184074852854127821",
                "token0": {
                    "symbol": "xSafeMars"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "35758.94243575404265658068535804367",
                "token0": {
                    "symbol": "AVE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "14791408.30692924087092406493833843",
                "token0": {
                    "symbol": "LINK.e"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "WET"
                }
            },
            {
                "reserveUSD": "99232.147123117207322321851304469",
                "token0": {
                    "symbol": "SPORE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "4247887.764222713043780735975677555",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "XAVA"
                }
            },
            {
                "reserveUSD": "2523.675207581219111277486658257504",
                "token0": {
                    "symbol": "EverAvax"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "4.993714692522419473404587059153483",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "Moon"
                }
            },
            {
                "reserveUSD": "0.0000000003461383007667237391651584433823788",
                "token0": {
                    "symbol": "xShibaInu"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "4.005091656045789265859736014737063",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "xShibaInu"
                }
            },
            {
                "reserveUSD": "3.370059618753180669057280110396769",
                "token0": {
                    "symbol": "AVAlonMars"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "106.8133036643120937822946200441174",
                "token0": {
                    "symbol": "USDT"
                },
                "token1": {
                    "symbol": "ETH"
                }
            },
            {
                "reserveUSD": "2632.421335951344326222241499686774",
                "token0": {
                    "symbol": "AVXT"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "177.4534076395387756926879098552591",
                "token0": {
                    "symbol": "CYCLE"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "14767409.87197375773918261158223374",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "DAI.e"
                }
            },
            {
                "reserveUSD": "989176.9875446271493726010035427943",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "ELK"
                }
            },
            {
                "reserveUSD": "0.4781155675019769522537938798337554",
                "token0": {
                    "symbol": "Bavax"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.04099339806784856337983463837676197",
                "token0": {
                    "symbol": "LINK"
                },
                "token1": {
                    "symbol": "PEFI"
                }
            },
            {
                "reserveUSD": "194608.6577674503608737266772048034",
                "token0": {
                    "symbol": "SafeMoonA"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "4138785.998151548732640717166643147",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "SNOB"
                }
            },
            {
                "reserveUSD": "1.385200108934067647547362226221116",
                "token0": {
                    "symbol": "JOE"
                },
                "token1": {
                    "symbol": "HAT"
                }
            },
            {
                "reserveUSD": "1131281.961236737467284518237678978",
                "token0": {
                    "symbol": "HUSKY"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "USELESS"
                }
            },
            {
                "reserveUSD": "1613.087226003759259667583219603661",
                "token0": {
                    "symbol": "DAI"
                },
                "token1": {
                    "symbol": "USDT"
                }
            },
            {
                "reserveUSD": "815606.152395314165743434173391437",
                "token0": {
                    "symbol": "SHIBX"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.00000000000001718087494627323966457564644683035",
                "token0": {
                    "symbol": "SUSHI"
                },
                "token1": {
                    "symbol": "PEFI"
                }
            },
            {
                "reserveUSD": "0.2608984529817568228114395971999726",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "LUX"
                }
            },
            {
                "reserveUSD": "3415.859502166448757961614712374473",
                "token0": {
                    "symbol": "MoonBear"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "11165977.15224778996721642122422471",
                "token0": {
                    "symbol": "USDC.e"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.0004485652613360158679846492843131731",
                "token0": {
                    "symbol": "test"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "21917569.38814979489132201712972553",
                "token0": {
                    "symbol": "USDT.e"
                },
                "token1": {
                    "symbol": "DAI.e"
                }
            },
            {
                "reserveUSD": "19201.87867589431173692851744138631",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "ZABU"
                }
            },
            {
                "reserveUSD": "274.0182031770326177256762165904984",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "🐆"
                }
            },
            {
                "reserveUSD": "2.458042461949533479181704633188726",
                "token0": {
                    "symbol": "AxR"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "12703.99618625873223037868709853775",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "LINK"
                }
            },
            {
                "reserveUSD": "9470.71728172016695761976432438978",
                "token0": {
                    "symbol": "xDoge"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1.088165953037291053871262736544747",
                "token0": {
                    "symbol": "Xshib"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.1550634820378714972114954905116704",
                "token0": {
                    "symbol": "PNG"
                },
                "token1": {
                    "symbol": "PEFI"
                }
            },
            {
                "reserveUSD": "0.1268786033826539579587009569687875",
                "token0": {
                    "symbol": "SNOB"
                },
                "token1": {
                    "symbol": "PEFI"
                }
            },
            {
                "reserveUSD": "0.001534580934400587742017319546648296",
                "token0": {
                    "symbol": "Babyavax"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "0.1366092788444968127876278827112693",
                "token0": {
                    "symbol": "GMR"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "8281445.29006168782383626337016605",
                "token0": {
                    "symbol": "YAK"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "36066.30491928070561726037524127031",
                "token0": {
                    "symbol": "AvaxMoon"
                },
                "token1": {
                    "symbol": "WAVAX"
                }
            },
            {
                "reserveUSD": "1335800.564816868818086135611448458",
                "token0": {
                    "symbol": "WAVAX"
                },
                "token1": {
                    "symbol": "PEFI"
                }
            }
        ]
    }
}

nd = {}

# for d in dic["data"]["pairs"]:
#     if float(d["reserveUSD"]) > 1e6:
#         nd["{}/{}".format(d["token0"]["symbol"], d["token1"]["symbol"])] = float(d["reserveUSD"])
#
# print({k: v for k, v in sorted(nd.items(), key=lambda item: item[1])})
