import asyncio

from app.services.retrieval.classifier import classify_query
from app.services.retrieval.graph import graph_retrieve
from app.services.retrieval.keyword import keyword_retrieve
from app.services.retrieval.merger import merge_and_rank
from app.services.retrieval.vector import vector_retrieve
from app.services.retrieval.web import web_retrieve

_RETRIEVERS = {
    "vector": vector_retrieve,
    "keyword": keyword_retrieve,
    "graph": graph_retrieve,
    "web": web_retrieve,
}


async def adaptive_retrieve(query: str) -> dict:
    """
    Classify query → run selected retrieval paths concurrently → merge & rank.

    Returns:
        results          – merged, ranked list of {"text", "score", "source", "metadata"}
        strategies_used  – strategies the classifier picked
        reasoning        – classifier's reasoning string
        source_counts    – {"vector": n, …} per path
    """
    classification = await classify_query(query)
    strategies: list[str] = classification["strategies"]
    reasoning: str = classification["reasoning"]

    tasks = {
        name: asyncio.create_task(fn(query))
        for name, fn in _RETRIEVERS.items()
        if name in strategies
    }

    results_by_source: dict[str, list[dict]] = {}
    for name, task in tasks.items():
        try:
            results_by_source[name] = await task
        except Exception:
            results_by_source[name] = []

    merged = merge_and_rank(results_by_source)

    return {
        "results": merged,
        "strategies_used": strategies,
        "reasoning": reasoning,
        "source_counts": {src: len(lst) for src, lst in results_by_source.items()},
    }
