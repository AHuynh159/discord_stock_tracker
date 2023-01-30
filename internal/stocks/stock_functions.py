import yfinance as yf

from collections import Counter

from datetime import datetime, timedelta
from pandas import DataFrame


async def get_price_by_date(ticker: bytes | str, date: str = None) -> DataFrame:
    if type(ticker) is bytes:
        ticker = ticker.decode("utf-8")

    # if no given date, take the most recent price
    date = datetime.strptime(date, r"%Y-%m-%d") - \
        timedelta(days=4) if date else datetime.today() - timedelta(days=4)
    df = yf.download(
        ticker,
        start=date,
        progress=False,
        threads=True,
    ).tail(1).reset_index()[['Date', 'Close']]
    df['Date'] = df['Date'].dt.date
    return df
