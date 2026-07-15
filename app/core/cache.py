import json
from typing import Any

import redis.asyncio as redis

from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


async def cache_get(key: str) -> Any | None:
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    await redis_client.set(key, json.dumps(value), ex=ttl_seconds)


async def cache_delete_prefix(prefix: str) -> None:
    # NOTE (m4): SCAN is O(N) on keyspace. Acceptable for MVP traffic
    # volumes but consider Redis key-space notifications or explicit
    # key tracking if you scale past ~10k cached keys.
    async for key in redis_client.scan_iter(match=f"{prefix}*"):
        await redis_client.delete(key)
