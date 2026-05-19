from app.services.knowledge_graph.searcher import graph_rag_search


async def graph_retrieve(query: str, limit: int = 5) -> list[dict]:
    """
    Full graph RAG: NL → Cypher (llama3.1) → Neo4j execute → ranked chunks.
    Falls back to empty list if Neo4j is unavailable or query produces no results.
    """
    return await graph_rag_search(query, limit=limit)
