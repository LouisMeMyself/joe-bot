import asyncio

import mplfinance as fplt

from joeBot import Constants, JoeSubGraph
from joeBot.JoeSubGraph import getTokenCandles


async def getTokenCandlesPerAvax(token_address, period, nb):
    token_candle = await getTokenCandles(token_address, period, nb)
    if token_address == Constants.WAVAX_ADDRESS:
        return token_candle[::-1]

    avax_candle = await getTokenCandles(Constants.WAVAX_ADDRESS, period, nb)

    avax_candle = avax_candle[:len(token_candle)]
    token_candle = token_candle[:len(avax_candle)]

    data_df = token_candle.mul(avax_candle)
    data_df = data_df.iloc[::-1]

    # TODO: add data when there is none
    # for i, row in data_df.iterrows():
    #
    #     print(row.index)

    return data_df


async def getChart(token_symbol, period):
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

    data_pd = await getTokenCandlesPerAvax(token_address, p, nb)
    fplt.plot(data_pd, type='candle',
              title='${} Price for the last {} {}.'.format(token_symbol.upper(),
                                                           len(data_pd), t),
              ylabel='price ($)', style='charles', savefig="content/images/chart.png")

if __name__ == '__main__':
    asyncio.run(JoeSubGraph.reloadAssets())
    asyncio.run(getChart("yak", "day"))
