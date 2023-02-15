import interactions
from . import helpers
from ..redis_connector import funcs as rds
from .stock_functions import get_price_by_date
from pandas import DataFrame
from table2ascii import table2ascii as t2a, PresetStyle
from typing import Any


async def send_weekly_notifications(
    bot: interactions.Client,
    r: Any,
    ctx: interactions.CommandContext = None,
):
    if ctx:
        msg = await ctx.send("One moment... This may take several seconds, depending on Yahoo Finance.")
        discord_ids = [ctx.author.id.__str__().encode("utf-8")]
    else:
        discord_ids: list[bytes] = await rds.get_all_discord_ids(r=r)

    msg_headers = [
        "Ticker",
        "Book Cost",
        "Current Price",
        "",
        "% Change",
    ]

    for id in discord_ids:

        if await rds.is_user_muted(r=r, discord_id=id):
            continue  # skip muted users

        tickers: list[bytes] = await rds.get_all_tickers_from_user(r=r, discord_id=id)
        curr_data: DataFrame = await get_price_by_date([t.decode("utf-8") for t in list(tickers)])

        msg_body, channel_id = await helpers.build_notification_rows(
            r=r,
            id=id,
            curr_data=curr_data
        )

        output = t2a(
            header=msg_headers,
            body=msg_body,
            style=PresetStyle.minimalist,
            first_col_heading=True,
        )

        disc_id = id.decode("utf-8")
        if not ctx:
            print(f"sending weekly notification for {id}")

            default_channel = r.hget(id, "USER_SETTINGS.DEFAULT_CHANNEL")
            if default_channel:
                channel_id = int(default_channel)
            channel = await interactions.get(bot, interactions.Channel, object_id=channel_id)
            await channel.send(f"<@{disc_id}> Weekly reminder of stocks you're tracking.\n```\n{output}\n```")
        else:
            await msg.edit(f"<@{disc_id}> Here's a list of stocks you're tracking.\n```\n{output}\n```")
