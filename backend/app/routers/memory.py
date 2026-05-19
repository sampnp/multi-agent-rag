from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["memory"])


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


@router.get("/history")
async def get_history(
    limit: int = Query(default=20, ge=1, le=100),
    token: str = Depends(_extract_bearer),
):
    """Short-term conversation history (last N turns)."""
    from app.services.memory.short_term import get_history
    return {"history": await get_history(limit=limit)}


@router.get("/episodes")
async def get_episodes(
    limit: int = Query(default=20, ge=1, le=100),
    token: str = Depends(_extract_bearer),
):
    """Episodic memory — timestamped conversation events."""
    from app.services.memory.episodic import get_recent
    return {"episodes": await get_recent(limit=limit)}


@router.get("/summary")
async def get_summary(token: str = Depends(_extract_bearer)):
    """Compressed conversation summary."""
    from app.services.memory.summary import get_summary
    return {"summary": await get_summary()}


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@router.post("/search")
async def search_memory(body: SearchRequest, token: str = Depends(_extract_bearer)):
    """Semantic search over past conversations."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    from app.database import qdrant_client
    from app.services.memory.semantic import search
    if not qdrant_client:
        return {"results": []}
    results = await search(body.query, qdrant_client, limit=body.limit)
    return {"results": results}


@router.get("/stats")
async def get_stats(token: str = Depends(_extract_bearer)):
    """Memory layer counts and metadata."""
    from app.database import qdrant_client
    from app.services.memory import episodic, semantic, short_term
    from app.services.memory.summary import get_summary

    hist = await short_term.get_history(limit=100)
    ep_count = await episodic.count()
    vec_count = await semantic.count(qdrant_client) if qdrant_client else 0
    mem_summary = await get_summary()

    return {
        "short_term_turns": len(hist),
        "episodic_events": ep_count,
        "vector_memories": vec_count,
        "has_summary": bool(mem_summary),
    }


@router.delete("/clear")
async def clear_memory(token: str = Depends(_extract_bearer)):
    """Wipe all memory layers."""
    from app.services.memory.manager import clear_all
    await clear_all()
    return {"cleared": True}
