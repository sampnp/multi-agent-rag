"""
Episodic memory: Redis sorted set of timestamped conversation events.
Key: memory:episodes
Score: unix timestamp (enables range queries and decay)
Member: JSON {"query": ..., "response": ..., "timestamp": float}
"""
import json
import time

from app.database import redis_client

_KEY = "memory:episodes"
_TTL = 86400 * 30  # 30-day TTL on the key


async def record(query: str, response: str) -> None:
    if not redis_client:
        return
    ts = time.time()
    member = json.dumps({"query": query, "response": response, "timestamp": ts})
    await redis_client.zadd(_KEY, {member: ts})
    await redis_client.expire(_KEY, _TTL)


async def get_recent(limit: int = 20) -> list[dict]:
    if not redis_client:
        return []
    try:
        raw = await redis_client.zrevrange(_KEY, 0, limit - 1, withscores=True)
        results = []
        for member, score in raw:
            entry = json.loads(member)
            entry["timestamp"] = score
            results.append(entry)
        return results
    except Exception:
        return []


async def count() -> int:
    if not redis_client:
        return 0
    return await redis_client.zcard(_KEY)


async def clear() -> None:
    if redis_client:
        await redis_client.delete(_KEY)
