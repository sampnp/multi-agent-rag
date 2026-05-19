from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


@router.get("/stats")
async def graph_stats(token: str = Depends(_extract_bearer)):
    """Count of each node type in the knowledge graph."""
    from app.database import neo4j_driver
    from app.services.knowledge_graph.searcher import get_entity_stats
    stats = await get_entity_stats(neo4j_driver)
    total = sum(stats.values())
    return {"stats": stats, "total_nodes": total}


@router.get("/entities")
async def list_entities(
    limit: int = Query(default=30, ge=1, le=200),
    token: str = Depends(_extract_bearer),
):
    """Most recently added entities across all types."""
    from app.database import neo4j_driver
    from app.services.knowledge_graph.searcher import get_recent_entities
    entities = await get_recent_entities(neo4j_driver, limit=limit)
    return {"entities": entities}


@router.get("/relationships")
async def list_relationships(
    limit: int = Query(default=50, ge=1, le=200),
    token: str = Depends(_extract_bearer),
):
    """Top relationships ordered by co-mention weight."""
    from app.database import neo4j_driver
    from app.services.knowledge_graph.searcher import get_relationships
    rels = await get_relationships(neo4j_driver, limit=limit)
    return {"relationships": rels}


class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def graph_search(body: SearchRequest, token: str = Depends(_extract_bearer)):
    """Natural-language query → Cypher → execute → return results + generated Cypher."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    from app.database import neo4j_driver
    from app.services.knowledge_graph.cypher_gen import nl_to_graph_results
    result = await nl_to_graph_results(body.query, neo4j_driver)
    return result


class IngestRequest(BaseModel):
    doc_id: str
    doc_name: str
    text: str


@router.post("/ingest")
async def manual_ingest(body: IngestRequest, token: str = Depends(_extract_bearer)):
    """Manually extract entities from arbitrary text and ingest into the graph."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    from app.database import neo4j_driver
    from app.services.knowledge_graph.extractor import extract_from_chunk
    from app.services.knowledge_graph.ingestion import ingest
    from app.services.knowledge_graph.schema import ensure_schema
    if not neo4j_driver:
        raise HTTPException(status_code=503, detail="Neo4j not available")
    await ensure_schema(neo4j_driver)
    extraction = await extract_from_chunk(body.text)
    counts = await ingest(body.doc_id, body.doc_name, extraction, neo4j_driver)
    return {"extraction": extraction, "ingested": counts}
