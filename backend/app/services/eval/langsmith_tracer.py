"""
Optional LangSmith run tracing.
Activated only when LANGSMITH_API_KEY is set in the environment.
Posts run start/end events to the LangSmith REST API (v1).
No-ops silently if not configured.
"""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from app.config import settings

_BASE = "https://api.smith.langchain.com"
_PROJECT = getattr(settings, "LANGSMITH_PROJECT", "enterprise-ai-os")


def _enabled() -> bool:
    key = getattr(settings, "LANGSMITH_API_KEY", None)
    return bool(key and key.strip())


def _headers() -> dict:
    return {
        "x-api-key": getattr(settings, "LANGSMITH_API_KEY", ""),
        "Content-Type": "application/json",
    }


async def _post(path: str, body: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{_BASE}{path}", json=body, headers=_headers())
    except Exception:
        pass  # tracing is best-effort


@asynccontextmanager
async def trace(name: str, inputs: dict) -> AsyncGenerator[dict, None]:
    """Context manager that wraps a call with a LangSmith run trace."""
    if not _enabled():
        yield {}
        return

    run_id = str(uuid.uuid4())
    start_time = time.time()

    await _post("/runs", {
        "id": run_id,
        "name": name,
        "run_type": "chain",
        "start_time": start_time,
        "inputs": inputs,
        "session_name": _PROJECT,
    })

    run_info = {"run_id": run_id}
    try:
        yield run_info
    finally:
        await _post(f"/runs/{run_id}", {
            "end_time": time.time(),
            "outputs": run_info.get("outputs", {}),
            "error": run_info.get("error"),
        })
