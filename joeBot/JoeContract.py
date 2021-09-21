import asyncio

from web3 import Web3

from joeBot import Constants, JoeSubGraph

# web3
from joeBot.Constants import E18

w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")


def getContractAsERC20(tokenAddress):
    return w3.eth.contract(address=tokenAddress, abi=Constants.ERC20_ABI)


joetoken_contract = getContractAsERC20(Constants.JOETOKEN_ADDRESS)
wavaxtoken_contract = getContractAsERC20(Constants.WAVAX_ADDRESS)
usdtetoken_contract = getContractAsERC20(Constants.USDTe_ADDRESS)
usdcetoken_contract = getContractAsERC20(Constants.USDCe_ADDRESS)
joefactory_contract = w3.eth.contract(address=Constants.JOEFACTORY_ADDRESS, abi=Constants.JOEFACTORY_ABI)


def getAvaxPrice():
    avaxPriceFromUsdte = getDerivedPrice(wavaxtoken_contract, usdtetoken_contract, Constants.WAVAXUSDTE_ADDRESS, False)
    avaxPriceFromUsdce = getDerivedPrice(wavaxtoken_contract, usdcetoken_contract, Constants.WAVAXUSDCE_ADDRESS, False)

    return ((avaxPriceFromUsdte + avaxPriceFromUsdce) // 2) / E18


def getReserves(token0Contract, token1Contract, pairAddress):
    decimalToken0 = int(token0Contract.functions.decimals().call())
    decimalToken1 = int(token1Contract.functions.decimals().call())

    reserveToken0 = int(token0Contract.functions.balanceOf(pairAddress).call()) * (int(10 ** (18 - decimalToken0)))
    reserveToken1 = int(token1Contract.functions.balanceOf(pairAddress).call()) * (int(10 ** (18 - decimalToken1)))

    return reserveToken0, reserveToken1


def getDerivedPrice(token0Contract, token1Contract, pairAddress, fromToken0):
    reserves = getReserves(token0Contract, token1Contract, pairAddress)
    if fromToken0:
        return reserves[0] * E18 // reserves[1]
    return reserves[1] * E18 // reserves[0]


def getJoePrice():
    derivedPrice = getDerivedPrice(joetoken_contract, wavaxtoken_contract, Constants.JOEWAVAX_ADDRESS, False)
    avaxPrice = getAvaxPrice()
    return derivedPrice * avaxPrice / E18


def getPairAddress(tokenAddress):
    # find the avax pair of that token
    try:
        if tokenAddress > Constants.WAVAX_ADDRESS:
            return joefactory_contract.functions.getPair(tokenAddress, Constants.WAVAX_ADDRESS).call()
        return joefactory_contract.functions.getPair(Constants.WAVAX_ADDRESS, tokenAddress).call()
    except:
        return None


def getDerivedPriceOfToken(tokenSymbol):
    tokenSymbol = tokenSymbol.lower().replace(" ", "")
    try:
        tokenAddress = Web3.toChecksumAddress(Constants.NAME2ADDRESS[tokenSymbol])
    except:
        return "Unknown Token Symbol"
    token_contract = getContractAsERC20(tokenAddress)
    pair_address = getPairAddress(tokenAddress)
    if pair_address is None:
        return "Can't find a pair with avax and that token"
    derivedPrice = getDerivedPrice(token_contract, wavaxtoken_contract, pair_address, False)
    return derivedPrice

def getPriceAndDerivedPriceOfToken(symbol):
    derivedPrice = getDerivedPriceOfToken(symbol)
    if derivedPrice == "Unknown Token Symbol" or derivedPrice == "Can't find a pair with avax and that token":
        return derivedPrice
    derivedPrice = int(derivedPrice)
    avaxPrice = getAvaxPrice()
    return derivedPrice / E18, (derivedPrice * avaxPrice) / E18

if __name__ == '__main__':
    asyncio.run(JoeSubGraph.reloadAssets())
    print(getAvaxPrice())
    print(getJoePrice())
    print(getPriceAndDerivedPriceOfToken("snob"))
