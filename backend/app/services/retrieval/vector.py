from app.database import get_qdrant
from app.services.document import search_documents


async def vector_retrieve(query: str, limit: int = 5) -> list[dict]:
    try:
        raw = await search_documents(query, get_qdrant(), limit=limit)
        return [
            {
                "text": r["text"],
                "score": float(r.get("score", 0.5)),
                "source": "vector",
                "metadata": {"doc_id": r.get("doc_id", "")},
            }
            for r in raw
        ]
    except Exception:
        return []
