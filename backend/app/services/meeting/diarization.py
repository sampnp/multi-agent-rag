"""
Simplified speaker diarization via silence-gap analysis on Whisper segments.
Groups consecutive segments separated by <0.5 s into the same speaker turn.
When the gap exceeds 0.5 s, cycles to the next speaker label.
Not as accurate as pyannote.audio but fully local and dependency-free.
"""

MAX_SPEAKERS = 4
GAP_THRESHOLD = 0.5  # seconds


def assign_speakers(segments: list[dict]) -> list[dict]:
    """
    Input : [{start, end, text}, ...]
    Output: [{speaker, start, end, text}, ...]
    """
    if not segments:
        return []

    speaker_idx = 0
    result = []
    prev_end = segments[0]["start"]

    for seg in segments:
        gap = seg["start"] - prev_end
        if gap > GAP_THRESHOLD and result:
            speaker_idx = (speaker_idx + 1) % MAX_SPEAKERS
        result.append({
            "speaker": f"Speaker {speaker_idx + 1}",
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
        })
        prev_end = seg["end"]

    return result


def merge_speaker_turns(diarized: list[dict]) -> list[dict]:
    """Merge consecutive segments from the same speaker into single turns."""
    if not diarized:
        return []
    merged = [diarized[0].copy()]
    for seg in diarized[1:]:
        last = merged[-1]
        if seg["speaker"] == last["speaker"]:
            last["text"] += " " + seg["text"]
            last["end"] = seg["end"]
        else:
            merged.append(seg.copy())
    return merged
