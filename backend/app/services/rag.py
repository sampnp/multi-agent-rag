from typing import AsyncGenerator

from ollama import AsyncClient
from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.services.document import search_documents

CHAT_MODEL = "llama3.1"
SYSTEM_PROMPT = (
    "You are an intelligent AI assistant with access to enterprise documents. "
    "Answer questions using the provided context. Be concise and accurate. "
    "If the context doesn't contain enough information, say so clearly."
)


async def rag_stream(query: str, qdrant: AsyncQdrantClient) -> AsyncGenerator[str, None]:
    chunks = await search_documents(query, qdrant, limit=5)

    if chunks:
        context = "\n\n---\n\n".join(
            f"[Source {i+1}] {c['text']}" for i, c in enumerate(chunks)
        )
        user_message = f"Context from documents:\n{context}\n\nQuestion: {query}"
    else:
        user_message = f"No relevant documents found.\n\nQuestion: {query}"

    client = AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")
    stream = await client.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        stream=True,
    )

    async for part in stream:
        token = part.message.content
        if token:
            yield token
