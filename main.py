
import asyncio
import datetime
import os
from datetime import date

import interactions
import redis
from discord.ext import tasks
from dotenv import load_dotenv

from internal.funcs.printflush import printFlush
from internal.redis_connector.data_types import *
from internal.redis_connector.funcs import *
from internal.stocks.notifications import *
from internal.stocks.stock_functions import *

load_dotenv()

intents = interactions.Intents.ALL
bot = interactions.Client(
    token=os.getenv("TOKEN"),
    intents=intents,
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
    printFlush(f"`/track` invoked by {ctx.author.name} ({ctx.author.id})")
    stock_ticker = stock_ticker.upper()
    
    # get stock price
    msg = await ctx.send("One moment... This may take several seconds, depending on Yahoo Finance.")
    price_data = await get_price_by_date(
        ticker=stock_ticker,
        date=start_date,
    )

    if price_data.empty:
        printFlush(
            f"`/{track.name}` `{stock_ticker}` `{book_cost}` `{start_date}` returned an empty DataFrame")
        await msg.edit("Could not find stock data. Make sure the date format and stock tickers/exchange are correct.")
    else:
        try:
            company = await get_name_from_ticker(ticker=stock_ticker)
            contents = f"Tracking `{company}` for `{stock_ticker}`\n"
            contents += "If this company is unexpected, make sure you specify the exchange. " \
                + "You can use my `/drop [ticker]` command to untrack this stock.\n"

        except Exception as e:
            printFlush(
                f"error occurred during `{get_name_from_ticker.__name__}`:\n{e}")
            contents = f"Tracking `{stock_ticker}`\n"

        ts = TrackedStock(
            ticker=stock_ticker,
            discord_channel=ctx.channel_id.__int__(),
            book_cost=price_data["Close"].values[0],
            start_date=start_date,
        )
        if book_cost:
            ts.book_cost = book_cost
            await msg.edit(contents + f"Using book cost of `{book_cost}`.")
        elif not start_date:
            ts.book_cost = price_data["Close"].values[0]
            ts.start_date = price_data["Date"].values[0]
            await msg.edit(
                contents +
                "No date or price was provided. Using latest price from `{p}`.".format(
                    p=ts.start_date
                ),
            )
        else:
            await msg.edit(
                contents +
                "Using `{p}` from `{d}` as book price.".format(
                    p=ts.book_cost,
                    d=start_date,
                ),
            )

        resp = await add_stock_to_user(
            r=r,
            discord_id=ctx.author.id,
            tracked_stock=ts,
        )
        if resp:
            printFlush(f"Added `{stock_ticker}` for `{ctx.author.id}`")
        else:
            printFlush(f"Updated `{stock_ticker}` for {ctx.author.id}")
        printFlush(f"`/{track.name}` complete")


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
    printFlush(
        f"`/{drop.name}` invoked by {ctx.author.name} ({ctx.author.id})")
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

    printFlush(f"`/{drop.name}` complete")


@bot.command()
async def mute(ctx: interactions.CommandContext):
    """Prevents the bot from mentioning/pinging you during updates."""
    printFlush(
        f"`/{mute.name}` invoked by {ctx.author.name} ({ctx.author.id})")
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.MUTED",
        1,
    )
    await ctx.send("You will no longer be pinged on weekly updates.",
                   ephemeral=True
                   )
    printFlush(f"`/{mute.name}` complete")


@bot.command()
async def unmute(ctx: interactions.CommandContext):
    """Allows the bot to mention/ping you during updates."""
    printFlush(
        f"`/{unmute.name}` invoked by {ctx.author.name} ({ctx.author.id})")
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.MUTED",
        0,
    )
    await ctx.send("You will now be pinged on weekly updates.",
                   ephemeral=True
                   )
    printFlush(f"`/{unmute.name}` complete")


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
            printFlush(f"Received DM from {msg.author} ({msg.author.id})")
            from_user = "({id}) Feedback from `{user}#{tag}`:\n".format(
                id=msg.author.id,
                user=msg.author.username,
                tag=msg.author.discriminator,
            )
            pics = "\n"
            if msg.attachments:
                for attachment in msg.attachments:
                    pics += f"{attachment.url}\n"
            await channel.send(from_user + msg.content + pics)
    elif msg.channel_id == os.getenv("FEEDBACK_CHANNEL") \
            and msg.author.id == os.getenv("ADMIN_ID") \
            and msg.content.split(" ")[0] == "!force_notify":

        if msg.content.split(" ")[1] == "all" \
            and bot.me.id == os.getenv("TEST_BOT_ID"):
            await send_weekly_notifications(bot=bot, r=r)

        await stock_update_user(
            bot=bot,
            r=r,
            id=msg.content.split(" ")[1].encode("utf-8")
        )
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
    printFlush(
        f"`/{update_me.name}` invoked by {ctx.author} ({ctx.author.id})")

    await stock_update_user(
        bot=bot,
        r=r,
        id=ctx.author.id.__str__().encode(),
        msg=await ctx.send("One moment... This may take several seconds, depending on Yahoo Finance.")
    )
    printFlush(f"`/{update_me.name} complete")


@bot.command()
async def make_this_my_default_channel(ctx: interactions.CommandContext):
    """Forces the bot to only use this channel when sending weekly notifications."""
    printFlush(
        f"`/{make_this_my_default_channel.name} invoked by {ctx.author} ({ctx.author.id})")
    r.hset(
        ctx.author.id.__int__(),
        "USER_SETTINGS.DEFAULT_CHANNEL",
        ctx.channel_id.__int__(),
    )
    await ctx.send("You will now only be pinged here during weekly notifications.", ephemeral=True)
    printFlush(f"`/{make_this_my_default_channel.name} complete")


@bot.event
async def on_ready():
    check_if_friday.start()
    printFlush("Bot is ready")


@tasks.loop(hours=12)
async def check_if_friday():
    printFlush(f"Checking if Friday: {date.today().weekday()==4}")
    if date.today().weekday() == 4:  # 4 = Friday
        check_if_4pm.start()
        check_if_friday.stop()


@tasks.loop(minutes=30)
async def check_if_4pm():
    printFlush(f"Checking if 4pm EST: {datetime.utcnow().hour==21}")
    if datetime.utcnow().hour == 21:  # 21 = 4pm est
        await send_weekly_notifications(bot=bot, r=r)
        printFlush("Weekly notification sent")
        await asyncio.sleep(60*60*24*5)
        check_if_friday.start()
        check_if_4pm.stop()


bot.start()
