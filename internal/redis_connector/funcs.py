import json
from pandas import DataFrame

from redis import Redis
from .data_types import TrackedStock

async def add_stock_to_profile(r: Redis, discord_id: int, tracked_stock: TrackedStock):
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    tracked_stock.start_price = round(tracked_stock.start_price, 2)
    r.hset(
        discord_id,
        tracked_stock.ticker,
        json.dumps(tracked_stock.to_dict(), indent=2, sort_keys=True, default=str).encode("utf-8")
    )


async def get_from_profile(r: Redis, discord_id: int, stock_ticker: str) -> DataFrame:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    price_data: bytes = r.hget(discord_id, str(stock_ticker))
    return json.loads(price_data)


async def drop_from_profile(r: Redis, discord_id: int, stock_ticker: str) -> bool:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    success = r.hdel(discord_id, stock_ticker)
    return success


def get_all_profiles(r: Redis):
    discord_ids: list[bytes] = r.scan_iter("")

    for id in discord_ids:
        print(r.hget(id))
    return None