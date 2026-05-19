"""
Short-term memory: Redis list of recent Q&A turns (sliding window).
Key: memory:short_term
Each element: JSON {"query": ..., "response": ..., "timestamp": float}
"""
import json
import time

from app.database import redis_client

_KEY = "memory:short_term"
_MAX_ENTRIES = 20


async def append(query: str, response: str) -> int:
    if not redis_client:
        return 0
    entry = json.dumps({"query": query, "response": response, "timestamp": time.time()})
    length = await redis_client.rpush(_KEY, entry)
    # Keep only the last _MAX_ENTRIES items
    if length > _MAX_ENTRIES:
        await redis_client.ltrim(_KEY, -_MAX_ENTRIES, -1)
    return min(length, _MAX_ENTRIES)


async def get_history(limit: int = 10) -> list[dict]:
    if not redis_client:
        return []
    try:
        raw_list = await redis_client.lrange(_KEY, -limit, -1)
        return [json.loads(r) for r in raw_list]
    except Exception:
        return []


async def trim_to(keep: int) -> None:
    if redis_client:
        await redis_client.ltrim(_KEY, -keep, -1)


async def clear() -> None:
    if redis_client:
        await redis_client.delete(_KEY)
