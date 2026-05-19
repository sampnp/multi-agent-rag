"""
Bridges voice input to the RAG pipeline.
Uses rag_stream() (fast, single-hop) rather than the full multi-agent pipeline
because voice requires low-latency responses.
"""
from typing import AsyncGenerator
from app.services.rag import rag_stream
from app.database import get_qdrant


async def stream_response(query: str) -> AsyncGenerator[str, None]:
    """Yield response tokens for a voice query using RAG."""
    qdrant = get_qdrant()
    async for token in rag_stream(query, qdrant):
        yield token
