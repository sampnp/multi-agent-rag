"""
Tracks per-agent success/failure counts and average steps in Redis.
Keys:
  eval:agent:{name}:successes  — integer counter
  eval:agent:{name}:failures   — integer counter
  eval:agent:{name}:total_time — float (seconds) sum (for avg latency)
  eval:agent:{name}:calls      — integer (for avg latency calculation)
"""
import time
import app.database as _db

_AGENTS = ["Planner", "Researcher", "Executor", "Critic", "Memory"]
_TTL = 60 * 60 * 24 * 30  # 30 days


def _rkey(agent: str, field: str) -> str:
    return f"eval:agent:{agent}:{field}"


async def record_success(agent_name: str, elapsed_ms: float = 0.0) -> None:
    try:
        r = _db.redis_client
        if not r:
            return
        pipe = r.pipeline()
        pipe.incr(_rkey(agent_name, "successes"))
        pipe.incrbyfloat(_rkey(agent_name, "total_ms"), elapsed_ms)
        pipe.incr(_rkey(agent_name, "calls"))
        for key in [_rkey(agent_name, f) for f in ("successes", "total_ms", "calls")]:
            pipe.expire(key, _TTL)
        await pipe.execute()
    except Exception:
        pass


async def record_failure(agent_name: str) -> None:
    try:
        r = _db.redis_client
        if not r:
            return
        pipe = r.pipeline()
        pipe.incr(_rkey(agent_name, "failures"))
        pipe.expire(_rkey(agent_name, "failures"), _TTL)
        await pipe.execute()
    except Exception:
        pass


async def get_stats() -> list[dict]:
    """Return per-agent stats list sorted by agent name."""
    try:
        r = _db.redis_client
        if not r:
            return []
        results = []
        for name in _AGENTS:
            pipe = r.pipeline()
            pipe.get(_rkey(name, "successes"))
            pipe.get(_rkey(name, "failures"))
            pipe.get(_rkey(name, "total_ms"))
            pipe.get(_rkey(name, "calls"))
            vals = await pipe.execute()
            successes = int(vals[0] or 0)
            failures = int(vals[1] or 0)
            total_ms = float(vals[2] or 0)
            calls = int(vals[3] or 0)
            avg_ms = round(total_ms / calls, 1) if calls > 0 else 0.0
            total = successes + failures
            results.append({
                "agent": name,
                "successes": successes,
                "failures": failures,
                "total": total,
                "success_rate": round(successes / total, 3) if total > 0 else None,
                "avg_latency_ms": avg_ms,
            })
        return results
    except Exception:
        return []
