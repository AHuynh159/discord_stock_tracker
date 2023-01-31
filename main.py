
import interactions
from discord.ext import tasks

import asyncio
import datetime
from datetime import date
from dotenv import load_dotenv
import os
import redis


from internal.stocks.stock_functions import *
from internal.redis_connector.data_types import *
from internal.redis_connector.funcs import *
from internal.stocks.notifications import *

load_dotenv()
bot = interactions.Client(
    token=os.getenv("TOKEN"),
    intents=interactions.Intents.DEFAULT,
)
r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    password=os.getenv("REDIS_PASSWORD"),
)


@bot.command(
    options=[
        interactions.Option(
            name="stock_ticker",
            description="Stock ticker. e.g. `QQQ` or `AC.TO` to specify the <exchange>.<ticker>",
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
    stock_ticker = stock_ticker.upper()
    # get stock price
    price_data = await get_price_by_date(
        ticker=stock_ticker,
        date=start_date,
    )

    if price_data.empty:
        await ctx.send("Could not find stock data. Make sure the date format and stock tickers/exchange are correct.",
                       ephemeral=True
                       )
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
        else:
            await ctx.send(
                "Using `{p}` from `{d}` as book price.".format(
                    p=ts.start_price,
                    d=start_date,
                ),
                ephemeral=True
            )

        await add_stock_to_user(
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
    stock_ticker = stock_ticker.upper()
    tracked_stock = await get_stock_from_user(
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
    stock_ticker = stock_ticker.upper()
    ok: bool = await drop_stock_from_user(
        r=r,
        discord_id=ctx.author.id.__int__(),
        stock_ticker=stock_ticker.__str__(),
    )

    if ok:
        await ctx.send(f"`{stock_ticker}` will no longer be tracked.", ephemeral=True)
    else:
        await ctx.send(f"Could not complete operation. Are you sure you're tracking `{stock_ticker}`?", ephemeral=True)


@bot.command()
async def mute(ctx: interactions.CommandContext):
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.MUTED",
        1,
    )
    await ctx.send("You will no longer be pinged on weekly updates.",
                   ephemeral=True
                   )


@bot.command()
async def unmute(ctx: interactions.CommandContext):
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.MUTED",
        0,
    )
    await ctx.send("You will now be pinged during on weekly updates.",
                   ephemeral=True
                   )


@bot.command()
async def notify(
    ctx: interactions.CommandContext
):
    await send_weekly_notifications(bot=bot, r=r)
    print("notified")


@bot.event
async def on_ready():
    check_if_friday.start()
    print("Bot is ready")


@tasks.loop(hours=12)
async def check_if_friday():
    if date.today().weekday() == 4:  # 4 = Friday
        check_if_4pm.start()
        check_if_friday.stop()


@tasks.loop(minutes=30)
async def check_if_4pm():
    if datetime.now().hour == 16:  # 16 = 4pm
        await send_weekly_notifications(bot=bot, r=r)
        await asyncio.sleep(60*60*24)
        check_if_friday.start()
        check_if_4pm.stop()


bot.start()
