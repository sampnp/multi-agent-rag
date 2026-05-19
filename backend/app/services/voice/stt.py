"""
Speech-to-text using faster-whisper (reuses model loaded by meeting/transcription.py).
Accepts raw audio bytes, writes to a temp file, transcribes, cleans up.
"""
import asyncio
import os
import tempfile


def _transcribe_bytes(audio_bytes: bytes) -> str:
    from app.services.meeting.transcription import _get_model  # lazy, shared model

    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        segments_iter, _ = model.transcribe(tmp_path, beam_size=3, word_timestamps=False)
        text = " ".join(s.text.strip() for s in segments_iter if s.text.strip())
        return text
    finally:
        os.unlink(tmp_path)


async def transcribe_bytes(audio_bytes: bytes) -> str:
    """Return transcript string from raw audio bytes (WebM/Opus or WAV)."""
    return await asyncio.get_event_loop().run_in_executor(None, _transcribe_bytes, audio_bytes)
