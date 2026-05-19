import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.database import get_qdrant
from app.services.rag import rag_stream

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


# ── Simple RAG (Phase 2, kept for backward compat) ───────────────────────────

@router.post("/rag")
async def chat_rag(body: ChatRequest, token: str = Depends(_extract_bearer)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def event_stream():
        try:
            async for token_text in rag_stream(body.message, get_qdrant()):
                yield f"data: {json.dumps({'token': token_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Multi-Agent Pipeline (Phase 3) ────────────────────────────────────────────

@router.post("/agent")
async def chat_agent(body: ChatRequest, token: str = Depends(_extract_bearer)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    request_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()

    from app.agents.nodes import status_queues
    from app.agents.graph import agent_graph

    status_queues[request_id] = queue

    initial_state = {
        "query": body.message,
        "request_id": request_id,
        "plan": [],
        "research_results": [],
        "draft_response": "",
        "critique": "",
        "is_acceptable": False,
        "final_response": "",
        "iteration": 0,
        "memory_context": {},
    }

    async def run_graph():
        try:
            await agent_graph.ainvoke(initial_state)
        except Exception as e:
            await queue.put({"type": "error", "payload": {"message": str(e)}})
            await queue.put(None)
        finally:
            status_queues.pop(request_id, None)

    asyncio.create_task(run_graph())

    async def event_stream():
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=120.0)
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'payload': {'message': 'Request timed out'}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
