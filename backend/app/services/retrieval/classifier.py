import json

from ollama import AsyncClient

from app.config import settings

_SYSTEM = """You are a query routing assistant. Decide which retrieval strategies to use for the query.

Available strategies:
- vector: semantic similarity search over uploaded documents (use for topics, concepts, summaries)
- keyword: exact BM25 keyword search over documents (use for specific names, IDs, codes, exact phrases)
- graph: knowledge graph search (use for relationship queries: "who works with", "connected to", "depends on")
- web: live web search (use for current events, recent news, real-time data not likely in uploaded docs)

Output ONLY valid JSON with no extra text:
{"strategies": ["strategy1"], "reasoning": "one line explanation"}

Always include at least "vector" unless the query is clearly about real-time/live data only."""


async def classify_query(query: str) -> dict:
    client = AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")
    resp = await client.chat(
        model="llama3.1",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Query: {query}"},
        ],
    )
    raw = (resp.message.content or "").strip()
    try:
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        result = json.loads(raw)
        valid = {"vector", "keyword", "graph", "web"}
        strategies = [s for s in result.get("strategies", ["vector"]) if s in valid]
        return {
            "strategies": strategies or ["vector"],
            "reasoning": str(result.get("reasoning", "")),
        }
    except Exception:
        return {"strategies": ["vector"], "reasoning": "Defaulting to vector search"}
