"""
LLM-based entity and relationship extraction from text chunks.
Uses llama3.1 via Ollama. Output is validated and sanitized.
"""
import json

from ollama import AsyncClient

from app.config import settings
from app.services.knowledge_graph.schema import VALID_LABELS, VALID_RELATIONS

_SYSTEM = """You are an expert information extraction assistant.
Extract named entities and relationships from the given text.

Entity types: Person, Organization, Project, Topic, Concept
Relationship types: WORKS_ON, BELONGS_TO, MENTIONS, RELATES_TO, DEPENDS_ON

Output ONLY valid JSON, no extra text:
{
  "entities": [
    {"type": "Person", "name": "...", "description": "one short phrase or empty"}
  ],
  "relationships": [
    {"from": "name", "from_type": "Label", "relation": "REL_TYPE", "to": "name", "to_type": "Label"}
  ]
}

Rules:
- Use exact entity names (no pronouns)
- Only include entities that are clearly named
- Maximum 10 entities and 10 relationships per chunk
- Prefer specific names over generic terms
- Omit entities/relationships if uncertain"""


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


def _validate(raw: dict) -> dict:
    entities = []
    for e in raw.get("entities", []):
        if (
            isinstance(e.get("name"), str)
            and e["name"].strip()
            and e.get("type") in VALID_LABELS - {"Document"}
        ):
            entities.append({
                "type": e["type"],
                "name": e["name"].strip()[:120],
                "description": str(e.get("description", ""))[:200],
            })

    relationships = []
    for r in raw.get("relationships", []):
        if (
            isinstance(r.get("from"), str)
            and isinstance(r.get("to"), str)
            and r.get("relation") in VALID_RELATIONS
            and r.get("from_type") in VALID_LABELS
            and r.get("to_type") in VALID_LABELS
        ):
            relationships.append({
                "from": r["from"].strip()[:120],
                "from_type": r["from_type"],
                "relation": r["relation"],
                "to": r["to"].strip()[:120],
                "to_type": r["to_type"],
            })

    return {"entities": entities[:10], "relationships": relationships[:10]}


async def extract_from_chunk(text: str) -> dict:
    """Returns {"entities": [...], "relationships": [...]}"""
    if len(text) < 100:
        return {"entities": [], "relationships": []}
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Text:\n{text[:2000]}"},
            ],
        )
        raw_text = (resp.message.content or "").strip()
        if "```" in raw_text:
            raw_text = raw_text.split("```")[1].removeprefix("json").strip()
        return _validate(json.loads(raw_text))
    except Exception:
        return {"entities": [], "relationships": []}


def merge_extractions(extractions: list[dict]) -> dict:
    """Merge entity/relationship lists from multiple chunks, dedup by name+type."""
    seen_entities: set[tuple] = set()
    seen_rels: set[tuple] = set()
    entities: list[dict] = []
    relationships: list[dict] = []

    for ex in extractions:
        for e in ex.get("entities", []):
            key = (e["type"], e["name"].lower())
            if key not in seen_entities:
                seen_entities.add(key)
                entities.append(e)
        for r in ex.get("relationships", []):
            key = (r["from"].lower(), r["relation"], r["to"].lower())
            if key not in seen_rels:
                seen_rels.add(key)
                relationships.append(r)

    return {"entities": entities, "relationships": relationships}
