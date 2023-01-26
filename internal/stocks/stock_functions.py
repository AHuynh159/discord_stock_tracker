import yfinance as yf

# from interactions import CommandContext
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


# async def send_weekly_notifications(ctx: CommandContext):
    
#     await ctx.send()
