"""
Audio transcription using faster-whisper (local, free, CPU/GPU).
Returns list of segments: {start, end, text}.
"""
from app.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


async def transcribe(file_path: str) -> dict:
    """
    Returns:
        transcript   – full text
        segments     – [{start, end, text}]
        duration     – total audio duration in seconds
        language     – detected language code
    """
    import asyncio

    def _run():
        model = _get_model()
        segments_iter, info = model.transcribe(file_path, beam_size=5, word_timestamps=False)
        segments = [
            {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments_iter
            if s.text.strip()
        ]
        transcript = " ".join(s["text"] for s in segments)
        return {
            "transcript": transcript,
            "segments": segments,
            "duration": round(info.duration, 1),
            "language": info.language,
        }

    return await asyncio.get_event_loop().run_in_executor(None, _run)
