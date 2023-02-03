import interactions
from . import helpers
from ..redis_connector import funcs as rds
from .stock_functions import get_price_by_date
from pandas import DataFrame
from redis import Redis
from table2ascii import table2ascii as t2a, PresetStyle


async def send_weekly_notifications(
    bot: interactions.Client,
    r: Redis,
    ctx: interactions.CommandContext = None,
):
    if ctx:
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
        # skip muted users
        if await rds.is_user_muted(r=r, discord_id=id):
            continue

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

        if not ctx:
            channel = await interactions.get(bot, interactions.Channel, object_id=channel_id)
            await channel.send("<@{disc_id}> Weekly reminder of stocks you're tracking.\n```\n{output}\n```"
                            .format(
                                disc_id=id.decode("utf-8"),
                                output=output
                            )
                            )
        else:
            await ctx.send("<@{disc_id}> Here's a list of stocks you're tracking.\n```\n{output}\n```"
                            .format(
                                disc_id=id.decode("utf-8"),
                                output=output
                            )
                            )
