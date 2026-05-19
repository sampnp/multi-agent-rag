"""
Graph RAG search: converts results from Neo4j into text chunks
suitable for injection into the LLM context.
"""
from app.database import neo4j_driver
from app.services.knowledge_graph.cypher_gen import nl_to_graph_results


async def graph_rag_search(query: str, limit: int = 5) -> list[dict]:
    """
    Generate Cypher from the query, execute it, format results as retrieval chunks.
    Returns list of {"text", "score", "source", "metadata"} compatible with merger.
    """
    if not neo4j_driver:
        return []
    try:
        result = await nl_to_graph_results(query, neo4j_driver)
        rows = result.get("rows", [])
        cypher = result.get("cypher", "")
        if not rows:
            return []

        chunks = []
        for row in rows[:limit]:
            text = " | ".join(f"{k}: {v}" for k, v in row.items() if v and v != "None")
            if text:
                chunks.append({
                    "text": text,
                    "score": 0.75,
                    "source": "graph",
                    "metadata": {"cypher": cypher},
                })
        return chunks
    except Exception:
        return []


async def get_entity_stats(driver) -> dict:
    """Return counts of each node type in the graph."""
    if not driver:
        return {}
    labels = ["Person", "Organization", "Project", "Topic", "Concept", "Document"]
    stats = {}
    try:
        async with driver.session() as session:
            for label in labels:
                result = await session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
                row = await result.single()
                stats[label] = row["cnt"] if row else 0
    except Exception:
        pass
    return stats


async def get_recent_entities(driver, limit: int = 30) -> list[dict]:
    """Return most recently added entities across all types."""
    if not driver:
        return []
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (n) WHERE n.created_at IS NOT NULL AND NOT n:Document "
                "RETURN labels(n)[0] AS type, n.name AS name, "
                "n.description AS description, n.created_at AS created_at "
                "ORDER BY n.created_at DESC LIMIT $limit",
                limit=limit,
            )
            return await result.data()
    except Exception:
        return []


async def get_relationships(driver, limit: int = 50) -> list[dict]:
    """Return recent relationships for display."""
    if not driver:
        return []
    try:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (a)-[r]->(b) "
                "WHERE NOT a:Document AND NOT b:Document "
                "RETURN labels(a)[0] AS from_type, a.name AS from_name, "
                "type(r) AS relation, labels(b)[0] AS to_type, b.name AS to_name, "
                "r.weight AS weight "
                "ORDER BY r.weight DESC LIMIT $limit",
                limit=limit,
            )
            return await result.data()
    except Exception:
        return []
