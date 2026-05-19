"""
Semantic / vector memory: Qdrant collection storing embedded Q&A pairs.
Enables similarity search over past conversations.
"""
import time
import uuid

from ollama import AsyncClient
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.services.memory.decay import score_memory

_COLLECTION = "memory_vectors"
_EMBED_DIM = 768
_EMBED_MODEL = "nomic-embed-text"


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def _embed(text: str) -> list[float]:
    resp = await _client().embeddings(model=_EMBED_MODEL, prompt=text)
    return resp.embedding


async def _ensure_collection(qdrant: AsyncQdrantClient) -> None:
    existing = [c.name for c in (await qdrant.get_collections()).collections]
    if _COLLECTION not in existing:
        await qdrant.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_EMBED_DIM, distance=Distance.COSINE),
        )


async def store(query: str, response: str, qdrant: AsyncQdrantClient) -> None:
    try:
        await _ensure_collection(qdrant)
        combined = f"Q: {query}\nA: {response}"
        vector = await _embed(combined)
        await qdrant.upsert(
            collection_name=_COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "query": query,
                        "response": response[:500],  # store preview only
                        "timestamp": time.time(),
                        "combined_text": combined[:800],
                    },
                )
            ],
        )
    except Exception:
        pass


async def search(query: str, qdrant: AsyncQdrantClient, limit: int = 3) -> list[dict]:
    try:
        await _ensure_collection(qdrant)
        vector = await _embed(query)
        resp = await qdrant.query_points(
            collection_name=_COLLECTION,
            query=vector,
            limit=limit * 2,  # over-fetch, then re-rank with decay
            with_payload=True,
        )
        results = []
        for pt in resp.points:
            ts = float(pt.payload.get("timestamp", time.time()))
            composite = score_memory(float(pt.score), ts)
            results.append({
                "query": pt.payload.get("query", ""),
                "response": pt.payload.get("response", ""),
                "timestamp": ts,
                "similarity": float(pt.score),
                "composite_score": composite,
            })
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        return results[:limit]
    except Exception:
        return []


async def count(qdrant: AsyncQdrantClient) -> int:
    try:
        info = await qdrant.get_collection(_COLLECTION)
        return info.points_count or 0
    except Exception:
        return 0


async def clear(qdrant: AsyncQdrantClient) -> None:
    try:
        existing = [c.name for c in (await qdrant.get_collections()).collections]
        if _COLLECTION in existing:
            await qdrant.delete_collection(_COLLECTION)
    except Exception:
        pass
