"""
Conversation summary memory: LLM-compressed history stored in Redis.
Triggered automatically when short-term memory exceeds a threshold.
"""
import json

from ollama import AsyncClient

from app.config import settings
from app.database import redis_client

_SUMMARY_KEY = "memory:summary"
_COMPRESSION_THRESHOLD = 15
_KEEP_AFTER_COMPRESSION = 5


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def get_summary() -> str:
    if not redis_client:
        return ""
    try:
        raw = await redis_client.get(_SUMMARY_KEY)
        return raw or ""
    except Exception:
        return ""


async def save_summary(text: str) -> None:
    if redis_client:
        await redis_client.setex(_SUMMARY_KEY, 86400 * 30, text)


async def generate_and_save(history: list[dict]) -> str:
    """Compress a list of {query, response} entries into a summary."""
    if not history:
        return ""
    turns = "\n".join(
        f"User: {h['query']}\nAssistant: {h['response'][:300]}"
        for h in history
    )
    system = (
        "You are a memory compression assistant. Summarize the following conversation history "
        "into 3-5 concise bullet points that capture the key topics, decisions, and facts discussed. "
        "Output ONLY the bullet points, no headers."
    )
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": turns},
            ],
        )
        summary = resp.message.content or ""
        await save_summary(summary)
        return summary
    except Exception:
        return ""


async def maybe_compress(short_term_length: int, history: list[dict]) -> bool:
    """If history is over threshold, compress older entries. Returns True if compressed."""
    if short_term_length < _COMPRESSION_THRESHOLD:
        return False
    # Compress everything except the last _KEEP_AFTER_COMPRESSION entries
    to_compress = history[:-_KEEP_AFTER_COMPRESSION]
    if to_compress:
        existing = await get_summary()
        combined = (existing + "\n\n" + json.dumps(to_compress)).strip() if existing else json.dumps(to_compress)
        await generate_and_save(json.loads(combined) if combined.startswith("[") else to_compress)
    return True


async def clear() -> None:
    if redis_client:
        await redis_client.delete(_SUMMARY_KEY)
