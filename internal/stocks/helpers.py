
import json
from .stock_functions import get_price_by_date
from pandas import DataFrame
from redis import Redis
from typing import Tuple


async def build_notification_rows(
    r: Redis,
    id: bytes,
    curr_data: DataFrame,
) -> Tuple[list, int]:

    msg_body = []
    count_channels = {}

    # get price, and pct change
    for ticker in curr_data["Close"].columns:
        curr_row = []

        tracked_data = json.loads(r.hget(id, ticker).decode("utf-8"))
        change = round(
            curr_data["Close"][ticker].values[0] - tracked_data["start_price"],
            2
        )
        pct_change = round(change/tracked_data["start_price"]*100, 2)
        if pct_change > 0:
            icon = "🟩"
        elif pct_change < 0:
            icon = "🟥"
        else:
            icon = "➖"

        # keep track of most frequent discord channel
        channel_id = tracked_data["discord_channel"]
        if channel_id in count_channels:
            count_channels[channel_id] += 1
        else:
            count_channels[channel_id] = 1

        curr_row.extend([
            ticker,
            tracked_data["start_price"],
            "{:.2f}".format(round(curr_data["Close"][ticker].values[0], 2)),
            icon,
            "{:.2f}%".format(pct_change),
        ]
        )
        msg_body.append(curr_row)

    return msg_body, max(count_channels, key=count_channels.get)
