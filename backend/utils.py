from functools import lru_cache

import aioredis
import motor.motor_asyncio

from backend.config import Settings


@lru_cache
def get_settings():
    return Settings()


async def get_db():
    settings = get_settings()
    return motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_client_url)["Url-Shortener"]


async def get_redis_server():
    settings = get_settings()
    return aioredis.from_url(settings.redis_server_url, db=0)
