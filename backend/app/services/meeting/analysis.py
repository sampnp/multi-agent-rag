"""
LLM-based meeting analysis: topics, action items, decisions, blockers.
Single-pass extraction for efficiency.
"""
import json

from ollama import AsyncClient

from app.config import settings

_SYSTEM = """You are an expert meeting analyst. Given a meeting transcript, extract structured information.

Output ONLY valid JSON with no extra text:
{
  "topics": ["topic1", "topic2"],
  "action_items": [
    {"task": "description", "owner": "person or team", "due": "timeframe or empty", "priority": "high|medium|low"}
  ],
  "decisions": [
    {"decision": "what was decided", "rationale": "why, or empty"}
  ],
  "blockers": [
    {"issue": "what is blocking", "owner": "who owns resolution", "blocks": "what it blocks"}
  ]
}

Rules:
- topics: 2-6 main themes discussed (strings)
- action_items: only concrete tasks with a clear owner
- decisions: things explicitly agreed upon
- blockers: things explicitly called out as blocking progress
- Return empty arrays if none found, never null"""


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def analyse_transcript(transcript: str) -> dict:
    # Trim to 3000 chars so it fits in the context window for smaller models
    text = transcript[:3000]
    if len(transcript) > 3000:
        text += "\n[transcript truncated]"

    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Transcript:\n{text}"},
            ],
        )
        raw = (resp.message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        result = json.loads(raw)
        return {
            "topics": [str(t) for t in result.get("topics", [])][:8],
            "action_items": _validate_list(result.get("action_items", []),
                                           ["task", "owner", "due", "priority"]),
            "decisions": _validate_list(result.get("decisions", []),
                                        ["decision", "rationale"]),
            "blockers": _validate_list(result.get("blockers", []),
                                       ["issue", "owner", "blocks"]),
        }
    except Exception:
        return {"topics": [], "action_items": [], "decisions": [], "blockers": []}


def _validate_list(items, required_keys: list[str]) -> list[dict]:
    result = []
    for item in items:
        if isinstance(item, dict):
            clean = {k: str(item.get(k, "")) for k in required_keys}
            result.append(clean)
    return result[:20]


async def segment_topics(transcript: str) -> list[dict]:
    """
    Split transcript into topic segments for richer display.
    Returns [{topic, start_snippet, end_snippet}]
    """
    if len(transcript) < 200:
        return []
    system = (
        "You are a meeting segmentation assistant. "
        "Identify the major topic transitions in this transcript and return "
        "ONLY valid JSON: [{\"topic\": \"name\", \"start_snippet\": \"first few words\"}]. "
        "Max 6 topics."
    )
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript[:2000]},
            ],
        )
        raw = (resp.message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        return json.loads(raw)[:6]
    except Exception:
        return []
