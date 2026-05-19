"""
Tone/emotion detection via llama3.1.
Returns one of: neutral, positive, frustrated, confused, excited, concerned.
"""
import asyncio
from ollama import AsyncClient
from app.config import settings

TONES = ["neutral", "positive", "frustrated", "confused", "excited", "concerned"]
_SYSTEM = (
    "You are a tone classifier. Given a user's spoken message, respond with exactly one word "
    "from this list: neutral, positive, frustrated, confused, excited, concerned. "
    "No explanation, no punctuation — just the single word."
)


async def detect_tone(text: str) -> str:
    """Return detected tone label for the given transcript."""
    if not text.strip():
        return "neutral"
    try:
        client = AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": text},
            ],
            stream=False,
        )
        label = resp.message.content.strip().lower().split()[0]
        return label if label in TONES else "neutral"
    except Exception:
        return "neutral"
