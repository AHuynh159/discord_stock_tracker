import yfinance as yf
from datetime import datetime, timedelta
from pandas import DataFrame


async def get_price_by_date(ticker: str, date: str) -> DataFrame:

    # if no given date, take the most recent price
    date = datetime.strptime(date, r"%Y-%m-%d") - \
        timedelta(days=4) if date else datetime.today() - timedelta(days=4)
    df = yf.download(ticker, start=date).tail(
        1).reset_index()[['Date', 'Close']]
    df['Date'] = df['Date'].dt.date
    return df


if __name__ == '__main__':  # for testing purposes
    date = datetime.today()
    date = date - \
        timedelta(days=4) if date else datetime.today() - timedelta(days=4)
    test = yf.download('MSFT', start=date).tail(
        1).reset_index()[['Date', 'Close']]
    print(test)
