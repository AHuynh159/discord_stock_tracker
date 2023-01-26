import interactions
from discord.ext import tasks
import os
import redis

from dotenv import load_dotenv
from internal.stocks.stock_functions import *
from internal.redis_connector.data_types import *
from internal.redis_connector.funcs import *

load_dotenv()

bot = interactions.Client(token=os.getenv("TOKEN"))
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
)


@bot.command(
    options=[
        interactions.Option(
            name="stock_ticker",
            description="Stock ticker. e.g. `QQQ` or `TSE.AC` to specify the <exchange>.<ticker>",
            type=interactions.OptionType.STRING,
            required=True,
        ),
        interactions.Option(
            name="start_price",
            description="Starting price to track the stock.",
            type=interactions.OptionType.NUMBER,
            required=False,
        ),
        interactions.Option(
            name="start_date",
            description="YYYY-MM-DD. Uses closing price at given date as starting price.",
            type=interactions.OptionType.STRING,
            required=False,
        )
    ]
)
async def track(
    ctx: interactions.CommandContext,
    stock_ticker: str,
    start_price: float = None,
    start_date: str = None,
):
    """Tracks a stock and sends a weekly Discord notification to provide price updates."""

    # get stock price
    price_data = await get_price_by_date(
        ticker=stock_ticker,
        date=start_date,
    )

    if price_data.empty:
        await ctx.send("Could not find stock data. \
            Make sure the date format and stock tickers are correct.", ephemeral=True)
    else:
        ts = TrackedStock(
            ticker=stock_ticker,
            discord_channel=ctx.channel_id.__int__(),
            start_price=price_data["Close"].values[0],
            start_date=start_date,
        )
        if start_price:
            ts.start_price = start_price
            await ctx.send(f"Tracking `{stock_ticker}` at price of `{start_price}`.", ephemeral=True)
        elif not start_date:
            ts.start_price = price_data["Close"].values[0]
            ts.start_date = price_data["Date"].values[0]
            await ctx.send(
                "No date or price was provided. Using latest price from `{p}`.".format(
                    p=ts.start_date),
                ephemeral=True
            )

        await add_stock_to_profile(
            r=r,
            discord_id=ctx.author.id,
            tracked_stock=ts,
        )


@bot.command(
    options=[
        interactions.Option(
            name="stock_ticker",
            description="Retrive data using a ticker.",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ]
)
async def get(
    ctx: interactions.CommandContext,
    stock_ticker: str,
):
    """Retrieves data stored in back-end. Mainly used for testing."""
    tracked_stock = await get_from_profile(
        r=r,
        discord_id=ctx.author.id.__int__(),
        stock_ticker=stock_ticker.__str__()
    )
    await ctx.send(tracked_stock.__str__(), ephemeral=True)


@bot.command(
    options=[
        interactions.Option(
            name="stock_ticker",
            description="Untracks a stock.",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ]
)
async def drop(
    ctx: interactions.CommandContext,
    stock_ticker: str,
):
    ok: bool = await drop_from_profile(
        r=r,
        discord_id=ctx.author.id.__int__(),
        stock_ticker=stock_ticker.__str__(),
    )

    if ok:
        await ctx.send(f"`{stock_ticker}` will no longer be tracked.", ephemeral=True)
    else:
        await ctx.send(f"Could not complete operation. Are you sure you're tracking `{stock_ticker}`?", ephemeral=True)


# @tasks.loop()


bot.start()
