import json
from typing import Any, Tuple, List

import interactions
import pandas as pd
from redis import Redis
from scipy import stats

from ..funcs.printflush import printFlush
from ..redis_connector import funcs as rds
from . import helpers
from .stock_functions import get_price_by_date, get_latest_price
from .data_types import NotificationRow


async def send_weekly_notifications(bot: interactions.Client, r: Any):
    discord_ids: list[bytes] = await rds.get_all_discord_ids(r=r)

    for id in discord_ids:
        await stock_update_user(bot, r, id)


async def build_notification_rows(
    r: Redis,
    id: bytes,
    latest_price: float,
    ticker: str,
) -> Tuple[list, int]:

    curr_row = NotificationRow(ticker=ticker)

    # retrieve stored data from redis
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

    # the row being built out
    curr_row.book_cost = round(tracked_data["book_cost"], 2)
    curr_row.current_price = round(latest_price, 2)

    curr_row.delta_tracked_icon = all_time_change_icon
    curr_row.delta_tracked_amount = all_time_change
    curr_row.delta_tracked_pct = str(all_time_pct_change) + "%"

    curr_row.delta_week_icon = last_week_change_icon
    curr_row.delta_week_amount = last_week_change
    curr_row.delta_week_pct = str(last_week_pct_change) + "%"

    return curr_row.__list__(), tracked_data["discord_channel"]


async def stock_update_user(
    bot: interactions.Client,
    r: Any,
    id: bytes,
    msg: interactions.Message = None,  # the bot's reply if invoked with /update_me
):
    if await rds.is_user_muted(r=r, discord_id=id):
        return  # skip muted users

    tickers: list[bytes] = await rds.get_all_tickers_from_user(r=r, discord_id=id)
    curr_data: pd.DataFrame = await get_price_by_date([t.decode("utf-8") for t in list(tickers)])
    disc_id = id.decode("utf-8")
    tables, channel_id = await build_table(r=r, disc_id=id, df=curr_data, tickers=tickers)

    if not msg:  # if not invoked by a user
        printFlush(f"sending weekly notification for {id}")

        default_channel = r.hget(id, "USER_SETTINGS.DEFAULT_CHANNEL")
        if default_channel:
            channel_id = int(default_channel)
        channel = await interactions.get(bot, interactions.Channel, object_id=channel_id)
        await channel.send(f"<@{disc_id}> Weekly reminder of stocks you're tracking.\n")
    else:
        await msg.edit(f"<@{disc_id}> Here's a list of stocks you're tracking.\n")
        channel_id = msg.channel_id.__str__()
        channel = await interactions.get(bot, interactions.Channel, object_id=channel_id)

    for table in tables:
        await channel.send("```" + table.__str__() + "```")


async def build_table(
    r: Redis,
    disc_id: int,
    tickers: str,
    df: pd.DataFrame
) -> Tuple[List[str], int]:
    msg_headers = [
        "Ticker",
        "Book Cost",
        "Current Price",
        " ",
        "$ Δ Since Tracked",
        "% Δ Since Tracked",
        "Δ From Last Week -->",
        "  ",
        "$",
        r"%",
    ]
    tables = []
    channel_ids = []

    curr_table = await helpers.pretty_table_defaults(headers=msg_headers)

    for ticker in [t.decode("utf-8") for t in tickers]:
        latest_price = await get_latest_price(df=df, ticker=ticker)
        curr_row, channel_id = await build_notification_rows(
            id=disc_id,
            r=r,
            latest_price=latest_price,
            ticker=ticker,
        )
        curr_table.add_row(curr_row)
        channel_ids.append(channel_id)

        # if table character length exceeds discord msg limit,
        # separate the table rows into list elements
        if len(curr_table.get_string()) > 2000:
            # work in progress
            curr_table.del_row(-1)
            tables.append(curr_table)
            curr_table = await helpers.pretty_table_defaults(headers=msg_headers)
            curr_table.add_row(curr_row)
    tables.append(curr_table)

    return tables, stats.mode(channel_ids, keepdims=True).mode[0]
