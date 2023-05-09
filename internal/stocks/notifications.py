import io
import json
from collections import Counter
from typing import Any, List, Tuple

import interactions
import numpy as np
import pandas as pd
from redis import Redis

from ..funcs.printflush import printFlush
from ..redis_connector import funcs as rds
from . import helpers
from .data_types import NotificationRow
from .stock_functions import get_latest_price, get_price_by_date


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

    # get % change and icon comparing today with last week's price
    try:
        last_week_price = (await get_price_by_date(ticker, "-7d"))["Close"].values[0]
        last_week_change = round(latest_price - last_week_price, 2)
        last_week_pct_change = round(
            last_week_change/last_week_price*100, 2)
    except Exception as e:
        printFlush(e)
        last_week_change = 0
        last_week_pct_change = 0

    # the row being built out
    curr_row.book_cost = round(tracked_data["book_cost"], 2)
    curr_row.current_price = round(latest_price, 2)

    curr_row.delta_tracked_amount = all_time_change
    curr_row.delta_tracked_pct = str(all_time_pct_change) + "%"

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
    table, channel_id = await build_weekly_table(r=r, disc_id=id, df=curr_data, tickers=tickers)

    # create table in memory and send to Discord channel
    with io.BytesIO() as buffer:
        buffer = io.BytesIO()
        await helpers.create_update_table(buffer, table)
        buffer.seek(0)
        file = interactions.File(fp=buffer, filename="table.png")

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
    await channel.send(None, files=file)


async def build_weekly_table(
    r: Redis,
    disc_id: int,
    tickers: str,
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, int]:
    msg_headers = [
        "Ticker",
        "Book Cost",
        "Current Price",
        "$ Δ Inception",
        "ROI Inception",
        # "Δ vs. Last Week -->",
        "$ Δ Weekly",
        "% Δ Weekly",
    ]
    channel_ids = []

    curr_table: pd.DataFrame = pd.DataFrame(columns=msg_headers)

    for ticker in [t.decode("utf-8") for t in tickers]:
        latest_price = await get_latest_price(df=df, ticker=ticker)
        curr_row, channel_id = await build_notification_rows(
            id=disc_id,
            r=r,
            latest_price=latest_price,
            ticker=ticker,
        )
        curr_table.loc[ticker] = np.array(curr_row)
        channel_ids.append(channel_id)

    counts = Counter(channel_ids)
    return curr_table, counts.most_common(1)[0][0]
