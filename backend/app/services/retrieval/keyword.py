from app.database import es_client

ES_INDEX = "document_chunks"


async def ensure_es_index() -> None:
    if not es_client:
        return
    try:
        exists = await es_client.indices.exists(index=ES_INDEX)
        if not exists:
            await es_client.indices.create(
                index=ES_INDEX,
                body={
                    "mappings": {
                        "properties": {
                            "doc_id": {"type": "keyword"},
                            "chunk_index": {"type": "integer"},
                            "text": {"type": "text", "analyzer": "english"},
                        }
                    }
                },
            )
    except Exception:
        pass


async def index_chunk(doc_id: str, chunk_index: int, text: str) -> None:
    if not es_client:
        return
    try:
        await ensure_es_index()
        await es_client.index(
            index=ES_INDEX,
            id=f"{doc_id}_{chunk_index}",
            document={"doc_id": doc_id, "chunk_index": chunk_index, "text": text},
        )
    except Exception:
        pass


async def keyword_retrieve(query: str, limit: int = 5) -> list[dict]:
    if not es_client:
        return []
    try:
        resp = await es_client.search(
            index=ES_INDEX,
            body={
                "query": {"match": {"text": {"query": query, "operator": "or"}}},
                "size": limit,
            },
        )
        results = []
        max_score = resp["hits"]["max_score"] or 1.0
        for hit in resp["hits"]["hits"]:
            results.append({
                "text": hit["_source"]["text"],
                "score": hit["_score"] / max_score,
                "source": "keyword",
                "metadata": {
                    "doc_id": hit["_source"].get("doc_id", ""),
                    "chunk_index": hit["_source"].get("chunk_index", 0),
                },
            })
        return results
    except Exception:
        return []
