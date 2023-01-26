from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TrackedStock:
    ticker: str
    discord_channel: int
    start_price: float
    start_date: datetime

    def to_dict(self):
        return asdict(self)


@dataclass
class DiscordUser:
    discord_id: int
    stocks: dict[str: TrackedStock]
