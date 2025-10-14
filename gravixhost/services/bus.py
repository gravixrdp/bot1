import os
import json
from typing import Any, Dict
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)


async def publish(channel: str, payload: Dict[str, Any]):
    await redis.publish(channel, json.dumps(payload))


async def set_key(key: str, value: str, ttl: int = 30):
    await redis.set(key, value, ex=ttl)