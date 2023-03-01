import json
from typing import Any, Tuple

import interactions
import numpy as np
import pandas as pd
import yfinance as yf
from redis import Redis
from table2ascii import PresetStyle
from table2ascii import table2ascii as t2a

from ..funcs.printflush import printFlush
from ..redis_connector import funcs as rds
from . import helpers
from .stock_functions import get_price_by_date


async def send_weekly_notifications(
    bot: interactions.Client,
    r: Any,
    ctx: interactions.CommandContext = None,
    force: int = None,
):
    if ctx:
        msg = await ctx.send("One moment... This may take several seconds, depending on Yahoo Finance.")
        discord_ids = [ctx.author.id.__str__().encode("utf-8")]
    elif force:
        discord_ids: list[int] = [force]
    else:
        discord_ids: list[bytes] = await rds.get_all_discord_ids(r=r)

    msg_headers = [
        "Ticker",
        "Book Cost",
        "Current Price",
        " ",
        "% Change\nSince Tracked",
        "Change From\nLast Week -->  ",
        "  ",
        "$$$",
        "%",
    ]

    for id in discord_ids:

        if await rds.is_user_muted(r=r, discord_id=id):
            continue  # skip muted users

        tickers: list[bytes] = await rds.get_all_tickers_from_user(r=r, discord_id=id)
        curr_data: pd.DataFrame = await get_price_by_date([t.decode("utf-8") for t in list(tickers)])

        msg_body, channel_id = await build_notification_rows(
            r=r,
            id=id,
            curr_data=curr_data,
            solo_ticker=tickers[0].decode(
                "utf-8") if not isinstance(curr_data.keys(), pd.MultiIndex) else None
        )

        output = t2a(
            header=msg_headers,
            body=msg_body,
            style=PresetStyle.minimalist,
            first_col_heading=True,
        )

        disc_id = id.decode("utf-8")
        if not ctx:
            printFlush(f"sending weekly notification for {id}")

            default_channel = r.hget(id, "USER_SETTINGS.DEFAULT_CHANNEL")
            if default_channel:
                channel_id = int(default_channel)
            channel = await interactions.get(bot, interactions.Channel, object_id=channel_id)
            await channel.send(f"<@{disc_id}> Weekly reminder of stocks you're tracking.\n```\n{output}\n```")
        else:
            await msg.edit(f"<@{disc_id}> Here's a list of stocks you're tracking.\n```\n{output}\n```")


async def build_notification_rows(
    r: Redis,
    id: bytes,
    curr_data: pd.DataFrame,
    solo_ticker: str,
) -> Tuple[list, int]:

    msg_body = []
    count_channels = {}

    # get price, and pct change
    for ticker in curr_data["Close"]:
        curr_row = []
        if not isinstance(curr_data.keys(), pd.MultiIndex):
            latest_price = curr_data["Close"].values[0]
            ticker = solo_ticker
        else:
            latest_price = curr_data["Close"][ticker].values[0]
        if np.isnan(latest_price):
            try:
                latest_price = yf.Ticker(ticker).fast_info.last_price
            except Exception as e:
                printFlush(
                    f"Error during {build_notification_rows.__name__}:\n{e}")
                # attempt to redownload
                latest_price = yf.download(ticker, period="5d").tail(1)[
                    "Close"].values[0]

        tracked_data = json.loads(r.hget(id, ticker).decode("utf-8"))

        # get % change and icon comparing today with book cost
        all_time_change = round(latest_price - tracked_data["book_cost"], 2)
        all_time_pct_change = round(
            all_time_change/tracked_data["book_cost"]*100, 2)
        all_time_change_icon = await helpers.get_change_icon(all_time_pct_change)

        # get % change and icon comparing today with last week's price
        try:
            last_week_price = (await get_price_by_date(ticker, "-7d"))["Close"].values[0]
            last_week_change = round(latest_price - last_week_price, 2)
            last_week_pct_change = round(
                last_week_change/last_week_price*100, 2)
            last_week_change_icon = await helpers.get_change_icon(last_week_pct_change)
        except Exception as e:
            printFlush(e)
            last_week_change = 0
            last_week_pct_change = 0
            last_week_change_icon = await helpers.get_change_icon(0)

        # keep track of most frequent discord channel
        channel_id = tracked_data["discord_channel"]
        if channel_id in count_channels:
            count_channels[channel_id] += 1
        else:
            count_channels[channel_id] = 1

        # the row being built out
        curr_row.extend([
            ticker,
            "${:.2f}".format(tracked_data["book_cost"]),
            "${:.2f}".format(round(latest_price, 2)),
            all_time_change_icon,
            "{:.2f}%".format(all_time_pct_change),
            " ",
            last_week_change_icon,
            "${:.2f}".format(last_week_change),
            "{:.2f}%".format(last_week_pct_change),
        ]
        )
        msg_body.append(curr_row)

    return msg_body, max(count_channels, key=count_channels.get)
