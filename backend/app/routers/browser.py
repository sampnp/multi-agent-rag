import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/browser", tags=["browser-agent"])

# Per-task SSE queues
_task_queues: dict[str, asyncio.Queue] = {}


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


class RunRequest(BaseModel):
    task: str


@router.get("/templates")
async def list_templates(token: str = Depends(_extract_bearer)):
    from app.services.browser.reporter import TEMPLATES
    return {"templates": TEMPLATES}


@router.post("/run")
async def run_browser_task(body: RunRequest, token: str = Depends(_extract_bearer)):
    """Start an autonomous browser task. Returns an SSE stream of step events."""
    if not body.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue

    async def _background():
        from app.services.browser.navigator import run_task
        try:
            await run_task(body.task, queue)
        except Exception as e:
            await queue.put({"type": "error", "payload": {"message": str(e)}})
            await queue.put(None)
        finally:
            _task_queues.pop(task_id, None)

    asyncio.create_task(_background())

    async def event_stream():
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=180.0)
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'error', 'payload': {'message': 'Task timed out'}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
