import mplfinance as fplt

from joeBot import Constants, JoeSubGraph
from joeBot.JoeSubGraph import getTokenCandles


def getTokenCandlesPerAvax(token_address, period, nb):
    token_candle = getTokenCandles(token_address, period, nb)
    if token_address == Constants.WAVAX_ADDRESS:
        return token_candle[::-1]

    avax_candle = getTokenCandles(Constants.WAVAX_ADDRESS, period, nb)

    avax_candle = avax_candle[:len(token_candle)]
    token_candle = token_candle[:len(avax_candle)]

    data_df = token_candle.mul(avax_candle)
    data_df = data_df.iloc[::-1]

    return data_df


def getChart(token_symbol, period):
    token_symbol = token_symbol.lower().replace(" ", "")
    try:
        if token_symbol == 'avax':
            token_address = Constants.WAVAX_ADDRESS
        else:
            token_address = Constants.NAME2ADDRESS[token_symbol]
    except KeyError:
        raise KeyError

    if period == "month":
        p, nb, t = "86400", "31", "days"
    elif period == "day":
        p, nb, t = "3600", "24", "hours"
    else:
        return

    data_pd = getTokenCandlesPerAvax(token_address, p, nb)
    try:
        fplt.plot(data_pd, type='candle',
                  title='${} Price for the last {} {}.'.format(token_symbol.upper(),
                                                               len(data_pd), t),
                  ylabel='price ($)', style='charles', savefig="content/images/chart.png")
    except FileNotFoundError:
        fplt.plot(data_pd, type='candle',
                  title='${} Price for the last {} {}.'.format(token_symbol.upper(),
                                                               len(data_pd), t),
                  ylabel='price ($)', style='charles')


if __name__ == '__main__':
    JoeSubGraph.reloadAssets()
    getChart("elk", "day")
