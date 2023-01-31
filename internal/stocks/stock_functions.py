import yfinance as yf

from datetime import datetime, timedelta
from pandas import DataFrame


async def get_price_by_date(ticker: bytes | str, date: str = None) -> DataFrame:

    if type(ticker) is bytes:
        ticker = ticker.decode("utf-8")

    # if no given date, take the most recent price
    # 4 day window to account for weekends
    if not date:
        date = datetime.today() - timedelta(days=4)
        end_date = None
    else:
        date = datetime.strptime(date, r"%Y-%m-%d") - timedelta(days=4)
        end_date = date + timedelta(days=4)

    df: DataFrame = yf.download(
        ticker,
        start=date,
        end=end_date,
        progress=False,
        threads=True,
    ).tail(1).reset_index()[['Date', 'Close']]

    if not df.empty:
        df['Date'] = df['Date'].dt.date
    df = df.round(2)
    return df
