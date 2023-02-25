
import json
import numpy as np
import pandas as pd
import yfinance as yf

from redis import Redis
from typing import Tuple
from ..funcs.printflush import printFlush


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
                printFlush(f"Error during {build_notification_rows.__name__}:\n{e}")
                # attempt to redownload
                latest_price = yf.download(ticker, period="5d").tail(1)[
                    "Close"].values[0]

        tracked_data = json.loads(r.hget(id, ticker).decode("utf-8"))
        change = round(
            latest_price - tracked_data["book_cost"],
            2
        )
        pct_change = round(change/tracked_data["book_cost"]*100, 2)
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
            tracked_data["book_cost"],
            "{:.2f}".format(round(latest_price, 2)),
            icon,
            "{:.2f}%".format(pct_change),
        ]
        )
        msg_body.append(curr_row)

    return msg_body, max(count_channels, key=count_channels.get)
