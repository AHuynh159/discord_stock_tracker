from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from pandas import DataFrame

from ..funcs.printflush import printFlush


async def get_price_by_date(ticker: bytes | str, date: str = None) -> DataFrame:

    if type(ticker) is bytes:
        ticker = ticker.decode("utf-8")

    # if no given date, take the most recent price
    # 4 day window to account for weekends
    if not date:
        start_date = datetime.today() - timedelta(days=5)
        end_date = None
    elif date == "-7d":
        start_date = datetime.today() - timedelta(days=7)
        end_date = start_date + timedelta(days=5)
    else:
        start_date = datetime.strptime(date, r"%Y-%m-%d") - timedelta(days=5)
        end_date = start_date + timedelta(days=5)

    df: DataFrame = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        progress=False,
        threads=True,
    )

    if date == "-7d":
        df = df.head(1).reset_index()
    else:
        df = df.tail(1).reset_index()

    try:
        df = df[['Datetime', 'Close']]
    except KeyError:
        df = df[['Date', 'Close']]

    if not df.empty:
        df.rename({"Datetime": "Date"}, axis="columns", inplace=True)
        df['Date'] = df['Date'].dt.date
    df = df.round(2)
    return df


async def get_latest_price(ticker: str, df: pd.DataFrame):
    # get latest price data. try/except in case bugs during grabbing price
    if not isinstance(df.keys(), pd.MultiIndex):
        latest_price = df["Close"].values[0]
    else:
        latest_price = df["Close"][ticker].values[0]
    if np.isnan(latest_price):
        try:
            latest_price = yf.Ticker(ticker).fast_info.last_price
        except Exception as e:
            printFlush(
                f"error during {get_latest_price.__name__}:\n{e}")
            # attempt redownload
            latest_price = yf.download(ticker, period=5).tail(1)[
                "Close"].values[0]
    return latest_price


async def get_name_from_ticker(ticker: str) -> str:
    return yf.Ticker(ticker=ticker).get_info()["longName"]
