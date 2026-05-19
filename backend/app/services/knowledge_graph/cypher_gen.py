"""
Natural-language → Cypher query generator.
Generates READ-ONLY Cypher using llama3.1, then executes it safely.
"""
import json
import re

from ollama import AsyncClient

from app.config import settings
from app.services.knowledge_graph.schema import SCHEMA_DESCRIPTION

_SYSTEM = f"""You are a Neo4j Cypher expert. Convert the user's natural-language question
into a valid READ-ONLY Cypher query using the schema below.

{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY a JSON object: {{"cypher": "MATCH ... RETURN ..."}}
- Use ONLY MATCH, WHERE, RETURN, WITH, LIMIT, ORDER BY (no CREATE/DELETE/SET/MERGE)
- Always include LIMIT (max 20)
- Return text-like fields: name, description, relation types
- If no good query is possible, return {{"cypher": "MATCH (n) RETURN n.name LIMIT 5"}}"""


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


_WRITE_PATTERN = re.compile(
    r"\b(CREATE|DELETE|DETACH|SET|MERGE|REMOVE|DROP|CALL|LOAD)\b",
    re.IGNORECASE,
)


def _is_safe(cypher: str) -> bool:
    """Reject any Cypher containing write or admin keywords."""
    return not bool(_WRITE_PATTERN.search(cypher))


async def generate_cypher(question: str) -> str:
    """Return a safe Cypher string for the given natural-language question."""
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": question},
            ],
        )
        raw = (resp.message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        parsed = json.loads(raw)
        cypher = str(parsed.get("cypher", "")).strip()
        if cypher and _is_safe(cypher):
            return cypher
    except Exception:
        pass
    return "MATCH (n) RETURN n.name AS name LIMIT 10"


async def execute_cypher(cypher: str, driver) -> list[dict]:
    """Execute a Cypher query and return rows as plain dicts."""
    if not driver or not _is_safe(cypher):
        return []
    try:
        async with driver.session() as session:
            result = await session.run(cypher)
            rows = await result.data()
            # Convert each row to plain strings for LLM consumption
            clean = []
            for row in rows[:20]:
                clean.append({k: str(v) for k, v in row.items()})
            return clean
    except Exception:
        return []


async def nl_to_graph_results(question: str, driver) -> dict:
    """Full pipeline: question → Cypher → execute → return results + Cypher."""
    cypher = await generate_cypher(question)
    rows = await execute_cypher(cypher, driver)
    return {"cypher": cypher, "rows": rows}
