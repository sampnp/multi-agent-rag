"""
Text-to-speech using edge-tts (free Microsoft Edge TTS, no API key).
Yields audio data as bytes chunks suitable for streaming over WebSocket.
"""
import asyncio
import tempfile
import os
from typing import AsyncGenerator


VOICE = "en-US-AriaNeural"


async def synthesize_stream(text: str) -> AsyncGenerator[bytes, None]:
    """Yield MP3 audio chunks for the given text using edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def synthesize_to_bytes(text: str) -> bytes:
    """Return full MP3 audio as bytes (for short utterances)."""
    import edge_tts

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)
