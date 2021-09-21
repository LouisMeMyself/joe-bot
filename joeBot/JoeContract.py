from web3 import Web3

from joeBot import Constants

# web3
from joeBot.Constants import E18

w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)
wavaxtoken_contract = w3.eth.contract(address=Constants.WAVAX_ADDRESS, abi=Constants.WAVAX_ABI)
usdtetoken_contract = w3.eth.contract(address=Constants.USDTe_ADDRESS, abi=Constants.USDTE_ABI)
usdcetoken_contract = w3.eth.contract(address=Constants.USDCe_ADDRESS, abi=Constants.USDCE_ABI)


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


if __name__ == '__main__':
    print(getAvaxPrice())
    print(getJoePrice())
