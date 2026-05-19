import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.meeting import Meeting

router = APIRouter(prefix="/meetings", tags=["meetings"])

MEETINGS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "meetings"
MEETINGS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
MAX_SIZE_MB = 200


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


def _meeting_response(m: Meeting) -> dict:
    return {
        "id": str(m.id),
        "original_name": m.original_name,
        "status": m.status,
        "duration_seconds": m.duration_seconds,
        "topics": m.topics or [],
        "action_items": m.action_items or [],
        "decisions": m.decisions or [],
        "blockers": m.blockers or [],
        "speakers": m.speakers or [],
        "transcript": m.transcript,
        "error_message": m.error_message,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.post("/upload", status_code=202)
async def upload_meeting(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_extract_bearer),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    meeting_id = uuid.uuid4()
    safe_name = f"{meeting_id}{ext}"
    file_path = MEETINGS_DIR / safe_name

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_SIZE_MB} MB)")
    file_path.write_bytes(content)

    # Stub user_id — replace with real JWT parsing if needed
    stub_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    meeting = Meeting(
        id=meeting_id,
        user_id=stub_user_id,
        filename=safe_name,
        original_name=file.filename or safe_name,
        file_path=str(file_path),
        status="processing",
    )
    db.add(meeting)
    await db.commit()

    # Background processing
    from app.services.meeting.pipeline import process_meeting
    from app.database import AsyncSessionLocal
    asyncio.create_task(_run_pipeline(meeting_id, str(file_path)))

    return {"id": str(meeting_id), "status": "processing", "original_name": meeting.original_name}


async def _run_pipeline(meeting_id: uuid.UUID, file_path: str) -> None:
    from app.database import AsyncSessionLocal
    from app.services.meeting.pipeline import process_meeting
    async with AsyncSessionLocal() as db:
        try:
            await process_meeting(meeting_id, file_path, db)
        except Exception:
            pass


@router.get("/")
async def list_meetings(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_extract_bearer),
):
    result = await db.execute(
        select(Meeting).order_by(Meeting.created_at.desc()).limit(limit)
    )
    meetings = result.scalars().all()
    return [_meeting_response(m) for m in meetings]


@router.get("/blockers")
async def list_blockers(
    limit: int = Query(default=30, ge=1, le=100),
    token: str = Depends(_extract_bearer),
):
    """All unresolved blockers and decisions tracked across meetings."""
    import json
    from app.database import redis_client
    if not redis_client:
        return {"blockers": [], "decisions": []}

    raw_blockers = await redis_client.zrevrange("meeting:blockers:unresolved", 0, limit - 1)
    raw_decisions = await redis_client.zrevrange("meeting:decisions:unresolved", 0, limit - 1)

    return {
        "blockers": [json.loads(b) for b in raw_blockers],
        "decisions": [json.loads(d) for d in raw_decisions],
    }


@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_extract_bearer),
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _meeting_response(meeting)


@router.post("/{meeting_id}/jira")
async def push_to_jira(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_extract_bearer),
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status != "ready":
        raise HTTPException(status_code=400, detail="Meeting not yet processed")

    from app.services.meeting.jira import create_issues
    issues = await create_issues(meeting.action_items or [])
    return {"issues": issues}


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_extract_bearer),
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    try:
        Path(meeting.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(meeting)
    await db.commit()
