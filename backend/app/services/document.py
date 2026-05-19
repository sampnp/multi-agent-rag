import uuid
import os
import asyncio
from pathlib import Path

from pypdf import PdfReader
from ollama import AsyncClient
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
COLLECTION = "documents"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def _split_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]


async def _ensure_collection(qdrant: AsyncQdrantClient):
    existing = [c.name for c in (await qdrant.get_collections()).collections]
    if COLLECTION not in existing:
        await qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


async def _embed(text: str) -> list[float]:
    client = AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")
    response = await client.embeddings(model=EMBED_MODEL, prompt=text)
    return response.embedding


async def process_document(doc_id: uuid.UUID, file_path: str, db: AsyncSession, qdrant: AsyncQdrantClient):
    try:
        reader = PdfReader(file_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(pages)
        chunks = _split_text(full_text)

        await _ensure_collection(qdrant)

        points: list[PointStruct] = []
        for i, chunk in enumerate(chunks):
            embedding = await _embed(chunk)
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "doc_id": str(doc_id),
                        "chunk_index": i,
                        "text": chunk,
                        "page": i,
                    },
                )
            )

        await qdrant.upsert(collection_name=COLLECTION, points=points)

        # Also index into Elasticsearch for BM25 keyword search
        try:
            from app.services.retrieval.keyword import index_chunk
            for i, chunk in enumerate(chunks):
                await index_chunk(str(doc_id), i, chunk)
        except Exception:
            pass

        # Extract entities + relationships and store in Neo4j knowledge graph
        try:
            from app.database import neo4j_driver
            from app.services.knowledge_graph.extractor import extract_from_chunk, merge_extractions
            from app.services.knowledge_graph.ingestion import ingest
            from app.services.knowledge_graph.schema import ensure_schema
            if neo4j_driver:
                await ensure_schema(neo4j_driver)
                # Extract from first 5 chunks (representative sample, avoids very long processing)
                sample_chunks = chunks[:5]
                extractions = []
                for chunk in sample_chunks:
                    ex = await extract_from_chunk(chunk)
                    extractions.append(ex)
                merged = merge_extractions(extractions)
                await ingest(str(doc_id), str(doc_id), merged, neo4j_driver)
        except Exception:
            pass

        await db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(status="ready", chunk_count=len(chunks), page_count=len(pages))
        )
        await db.commit()

    except Exception as e:
        await db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(status="error", error_message=str(e))
        )
        await db.commit()
        raise


async def search_documents(query: str, qdrant: AsyncQdrantClient, limit: int = 5) -> list[dict]:
    await _ensure_collection(qdrant)
    query_vector = await _embed(query)
    response = await qdrant.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return [
        {"text": r.payload["text"], "doc_id": r.payload["doc_id"], "score": r.score}
        for r in response.points
    ]
