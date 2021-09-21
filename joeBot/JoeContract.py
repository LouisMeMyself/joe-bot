from web3 import Web3

from joeBot import Constants

# web3
from joeBot.Constants import E12, E18

w3 = Web3(Web3.HTTPProvider("https://api.avax.network/ext/bc/C/rpc"))
if not w3.isConnected():
    print("Error web3 can't connect")
joetoken_contract = w3.eth.contract(address=Constants.JOETOKEN_ADDRESS, abi=Constants.JOETOKEN_ABI)
wavaxtoken_contract = w3.eth.contract(address=Constants.WAVAX_ADDRESS, abi=Constants.WAVAX_ABI)
usdtetoken_contract = w3.eth.contract(address=Constants.USDTe_ADDRESS, abi=Constants.USDTE_ABI)


# const usdte_avax_pair_reserves = {
#           reserve_token: (
#             await this.usdte_contract.balanceOf(
#               Address[this.state.network_ID].usdte_wavax_pair
#             )
#           ).mul(BigNumber.from("10").pow("12")),
#           reserve_avax: await this.wavax_contract.balanceOf(
#             Address[this.state.network_ID].usdte_wavax_pair
#           ),
#         };
#         const hat_avax_pair_reserves = {
#           reserve_token: await this.hat_contract.balanceOf(
#             Address[this.state.network_ID].hat_wavax_pair
#           ),
#           reserve_avax: await this.wavax_contract.balanceOf(
#             Address[this.state.network_ID].hat_wavax_pair
#           ),
#         };

# float(w3.fromWei(joetoken_contract.functions.balanceOf(Constants.JOEBAR_ADDRESS).call(), 'ether'))

def getReserves():
    reserves = {}
    reserves["usdte_wavax"] = {
        "reserveToken0": int(int(usdtetoken_contract.functions.balanceOf(Constants.WAVAXUSDTE_ADDRESS).call()) * E12),
        "reserveToken1": int(wavaxtoken_contract.functions.balanceOf(Constants.WAVAXUSDTE_ADDRESS).call())}
    reserves["joe_wavax"] = {
        "reserveToken0": int(joetoken_contract.functions.balanceOf(Constants.JOEWAVAX_ADDRESS).call()),
        "reserveToken1": int(wavaxtoken_contract.functions.balanceOf(Constants.JOEWAVAX_ADDRESS).call())}
    reserves["joe_usdte"] = {
        "reserveToken0": int(joetoken_contract.functions.balanceOf(Constants.JOEUSDTE_ADDRESS).call()),
        "reserveToken1": int(usdtetoken_contract.functions.balanceOf(Constants.JOEUSDTE_ADDRESS).call()) * E12}
    return reserves


def getJoePrice():
    reserves = getReserves()
    avaxPrice = getTokenBalance(reserves["usdte_wavax"], False)
    joeDerivedPrice = getTokenBalance(reserves["joe_wavax"])
    joePrice = getTokenBalance(reserves["joe_usdte"])
    return (joeDerivedPrice * avaxPrice // E18 + joePrice) / 2e18


def getTokenBalance(data, derived=True):
    if not derived:
        return data["reserveToken0"] * E18 // data["reserveToken1"]

    return data["reserveToken1"] * E18 // data["reserveToken0"]


if __name__ == '__main__':
    print(getJoePrice())
