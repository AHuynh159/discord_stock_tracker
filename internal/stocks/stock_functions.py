from datetime import datetime, timedelta

import yfinance as yf
from pandas import DataFrame


async def get_price_by_date(ticker: bytes | str, date: str = None) -> DataFrame:

    if type(ticker) is bytes:
        ticker = ticker.decode("utf-8")

    # if no given date, take the most recent price
    # 4 day window to account for weekends
    if not date:
        date = datetime.today() - timedelta(days=5)
        end_date = None
    elif date == "-7d":
        date = datetime.today() - timedelta(days=7)
        end_date = date + timedelta(days=5)
    else:
        date = datetime.strptime(date, r"%Y-%m-%d") - timedelta(days=5)
        end_date = date + timedelta(days=5)

    df: DataFrame = yf.download(
        ticker,
        start=date,
        end=end_date,
        progress=False,
        threads=True,
    ).tail(1).reset_index()
    try:
        df = df[['Datetime', 'Close']]
    except KeyError:
        df = df[['Date', 'Close']]

    if not df.empty:
        df.rename({"Datetime": "Date"}, axis="columns", inplace=True)
        df['Date'] = df['Date'].dt.date
    df = df.round(2)
    return df


async def get_name_from_ticker(ticker: str) -> str:
    return yf.Ticker(ticker=ticker).get_info()["longName"]
