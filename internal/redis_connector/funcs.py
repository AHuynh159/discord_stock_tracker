import json
from pandas import DataFrame

from redis import Redis
from .data_types import TrackedStock


async def add_stock_to_user(r: Redis, discord_id: int, tracked_stock: TrackedStock):
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    tracked_stock.book_cost = round(tracked_stock.book_cost, 2)
    r.hset(
        discord_id,
        tracked_stock.ticker,
        json.dumps(tracked_stock.to_dict(), indent=2,
                   sort_keys=True, default=str).encode("utf-8")
    )


async def get_stock_from_user(r: Redis, discord_id: int, stock_ticker: str) -> DataFrame:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    price_data: bytes = r.hget(discord_id, str(stock_ticker))
    return json.loads(price_data)


async def drop_stock_from_user(r: Redis, discord_id: int, stock_ticker: str) -> bool:
    if type(discord_id) is not int:
        discord_id = discord_id.__int__()

    success = r.hdel(discord_id, stock_ticker)
    return success


async def get_all_discord_ids(r: Redis) -> list[bytes]:
    return list(r.scan_iter(_type="HASH"))


async def get_all_tickers_from_user(r: Redis, discord_id: int) -> list[bytes]:
    unfiltered = list(r.hgetall(discord_id))
    return [i for i in unfiltered if "USER_SETTINGS." not in i.decode("utf=8")]


async def is_user_muted(r: Redis, discord_id: int) -> bool:
    resp = r.hget(discord_id, "USER_SETTINGS.MUTED")
    if resp:
        return int(resp) == 1
    else:
        return resp


async def is_user_fb_blacklisted(r: Redis, discord_id: int) -> bool:
    resp = r.hget(discord_id, "USER_SETTINGS.FEEDBACK_BLACKLISTED")
    if resp:
        return int(resp) == 1
    else:
        return resp
