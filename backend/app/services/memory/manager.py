"""
MemoryManager: unified interface over all memory layers.
"""
from app.services.memory import episodic, semantic, short_term, summary


async def retrieve_context(query: str) -> dict:
    """
    Pull relevant memories before responding.
    Returns:
        recent_history  – last 5 turns (short-term)
        relevant        – semantically similar past Q&A (vector)
        summary         – compressed older history
    """
    from app.database import qdrant_client

    recent = await short_term.get_history(limit=5)
    mem_summary = await summary.get_summary()

    relevant: list[dict] = []
    if qdrant_client:
        relevant = await semantic.search(query, qdrant_client, limit=3)

    return {
        "recent_history": recent,
        "relevant_memories": relevant,
        "summary": mem_summary,
    }


async def save(query: str, response: str) -> dict:
    """
    Save a completed Q&A to all memory layers.
    Returns a dict describing what was saved (for SSE trace).
    """
    from app.database import qdrant_client

    length = await short_term.append(query, response)
    await episodic.record(query, response)

    if qdrant_client:
        await semantic.store(query, response, qdrant_client)

    # Compression check
    compressed = False
    if length >= summary._COMPRESSION_THRESHOLD:
        history = await short_term.get_history(limit=length)
        compressed = await summary.maybe_compress(length, history)
        if compressed:
            await short_term.trim_to(summary._KEEP_AFTER_COMPRESSION)

    return {
        "short_term_entries": length,
        "compressed": compressed,
        "episode_recorded": True,
        "vector_stored": qdrant_client is not None,
    }


async def clear_all() -> None:
    from app.database import qdrant_client
    await short_term.clear()
    await episodic.clear()
    await summary.clear()
    if qdrant_client:
        await semantic.clear(qdrant_client)
