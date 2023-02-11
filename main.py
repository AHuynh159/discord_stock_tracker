
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
            description="Ticker. e.g. `QQQ` or `AC.TO` to specify the <ticker>.<exchange>. Press Tab for optional inputs.",
            type=interactions.OptionType.STRING,
            required=True,
        ),
        interactions.Option(
            name="book_cost",
            description="(Optional) Book cost to track the stock.",
            type=interactions.OptionType.NUMBER,
            required=False,
        ),
        interactions.Option(
            name="start_date",
            description="(Optional) YYYY-MM-DD. Uses closing price at given date as starting price.",
            type=interactions.OptionType.STRING,
            required=False,
        )
    ]
)
async def track(
    ctx: interactions.CommandContext,
    stock_ticker: str,
    book_cost: float = None,
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
        # company = await get_name_from_ticker(ticker=stock_ticker) # currently bugged
        # msg = f"Tracking `{company}` for `{stock_ticker}`\n"
        # msg += "If this company is unexpected, make sure you specify the exchange.\n"

        msg = f"Tracking `{stock_ticker}`\n"

        ts = TrackedStock(
            ticker=stock_ticker,
            discord_channel=ctx.channel_id.__int__(),
            book_cost=price_data["Close"].values[0],
            start_date=start_date,
        )
        if book_cost:
            ts.book_cost = book_cost
            await ctx.send(msg + f"Using book cost of `{book_cost}`.", ephemeral=True)
        elif not start_date:
            ts.book_cost = price_data["Close"].values[0]
            ts.start_date = price_data["Date"].values[0]
            await ctx.send(
                msg +
                "No date or price was provided. Using latest price from `{p}`.".format(
                    p=ts.start_date),
                ephemeral=True
            )
        else:
            await ctx.send(
                msg +
                "Using `{p}` from `{d}` as book price.".format(
                    p=ts.book_cost,
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
            description="Specify a ticker to untrack.",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ]
)
async def drop(
    ctx: interactions.CommandContext,
    stock_ticker: str,
):
    """Untracks a stock from your weekly notification."""
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
    """Prevents the bot from mentioning/pinging you during updates."""
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
    """Allows the bot to mention/ping you during updates."""
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.MUTED",
        0,
    )
    await ctx.send("You will now be pinged on weekly updates.",
                   ephemeral=True
                   )


@bot.event
async def on_message_create(msg: interactions.Message):
    if msg.author.id == bot.me.id:
        return

    channel: interactions.Channel = await interactions.get(
        bot,
        interactions.Channel,
        object_id=os.getenv("FEEDBACK_CHANNEL")
    )

    if not msg.guild_id:

        if not await is_user_fb_blacklisted(r=r, discord_id=msg.author.id.__int__()):

            from_user = "({id}) Feedback from `{user}#{tag}`:\n".format(
                id=msg.author.id,
                user=msg.author.username,
                tag=msg.author.discriminator,
            )
            await channel.send(from_user + msg.content)

    elif msg.channel_id == os.getenv("FEEDBACK_CHANNEL") \
            and msg.author.id == os.getenv("ADMIN_ID") \
            and msg.message_reference:

        bot_msg = await channel.get_message(msg.message_reference.message_id.__int__())

        text: str = bot_msg.content
        start, end = text.find("(")+1, text.find(")")
        discord_id = text[start:end]
        if msg.content.lower() == "blacklist":
            r.hset(
                discord_id,
                "USER_SETTINGS.FEEDBACK_BLACKLISTED",
                1
            )

        if msg.content.lower() == "unblacklist":
            r.hset(
                discord_id,
                "USER_SETTINGS.FEEDBACK_BLACKLISTED",
                0
            )


@bot.command()
async def update_me(ctx: interactions.CommandContext):
    """Provide current status update on stocks you're tracking."""
    await send_weekly_notifications(bot=bot, r=r, ctx=ctx)


@bot.command()
async def make_this_my_default_channel(ctx: interactions.CommandContext):
    """Forces the bot to only use this channel when sending weekly notifications."""
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.DEFAULT_CHANNEL",
        ctx.channel_id.__int__(),
    )
    await ctx.send("You will now only be pinged here during weekly notifications.")


@bot.event
async def on_ready():
    check_if_friday.start()
    print("Bot is ready")


@tasks.loop(hours=12)
async def check_if_friday():
    print("Checking if Friday")
    if date.today().weekday() == 4:  # 4 = Friday
        check_if_4pm.start()
        check_if_friday.stop()


@tasks.loop(minutes=30)
async def check_if_4pm():
    if datetime.utcnow().hour == 21:  # 21 = 4pm est
        await send_weekly_notifications(bot=bot, r=r)
        print("Weekly notification sent")
        await asyncio.sleep(60*60*24)
        check_if_friday.start()
        check_if_4pm.stop()


bot.start()
