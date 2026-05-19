import asyncio


async def web_retrieve(query: str, limit: int = 5) -> list[dict]:
    try:
        from duckduckgo_search import DDGS

        def _search() -> list[dict]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=limit))

        raw = await asyncio.get_event_loop().run_in_executor(None, _search)
        return [
            {
                "text": f"{r.get('title', '')}: {r.get('body', '')}",
                "score": 0.72,
                "source": "web",
                "metadata": {"url": r.get("href", ""), "title": r.get("title", "")},
            }
            for r in raw
            if r.get("body")
        ]
    except Exception:
        return []
