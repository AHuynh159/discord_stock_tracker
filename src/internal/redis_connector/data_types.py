from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrackedStock:
    ticker: str
    discord_channel: int
    start_price: float
    start_date: datetime


@dataclass
class DiscordUser:
    discord_id: int
    stocks: dict[str: TrackedStock]
