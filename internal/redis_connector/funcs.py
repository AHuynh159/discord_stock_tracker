from pandas import DataFrame
import pickle

from redis import Redis
from .data_types import TrackedStock


async def add_stock_to_profile(r: Redis, discord_id: int, tracked_stock: TrackedStock):
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    tracked_stock.start_price = round(tracked_stock.start_price, 2)
    r.hset(
        discord_id,
        tracked_stock.ticker,
        pickle.dumps(tracked_stock, -1)
    )


async def get_from_profile(r: Redis, discord_id: int, stock_ticker: str) -> DataFrame:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    price_data: bytes = r.hget(discord_id, str(stock_ticker))
    print(pickle.loads(price_data))
    return pickle.loads(price_data)


async def drop_from_profile(r: Redis, discord_id: int, stock_ticker: str) -> bool:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    success = r.hdel(discord_id, stock_ticker)
    return success
