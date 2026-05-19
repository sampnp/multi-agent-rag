import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_qdrant
from app.models.document import Document
from app.services.auth import auth_service
from app.services.document import UPLOAD_DIR, process_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


class DocumentOut(BaseModel):
    id: uuid.UUID
    original_name: str
    status: str
    chunk_count: int
    page_count: int
    error_message: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    token: str = Depends(_extract_bearer),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    user = await auth_service.get_current_user(db, token)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}.pdf"
    file_path = UPLOAD_DIR / safe_name

    with file_path.open("wb") as f:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 50 MB)")
        f.write(contents)

    doc = Document(
        user_id=user.id,
        filename=safe_name,
        original_name=file.filename or "upload.pdf",
        file_path=str(file_path),
        status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    background_tasks.add_task(_process_in_background, doc.id, str(file_path))

    return _to_out(doc)


async def _process_in_background(doc_id: uuid.UUID, file_path: str):
    from app.database import AsyncSessionLocal, get_qdrant as _get_qdrant
    async with AsyncSessionLocal() as db:
        await process_document(doc_id, file_path, db, _get_qdrant())


@router.get("/", response_model=list[DocumentOut])
async def list_documents(
    token: str = Depends(_extract_bearer),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.get_current_user(db, token)
    result = await db.execute(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    return [_to_out(d) for d in result.scalars().all()]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    token: str = Depends(_extract_bearer),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.get_current_user(db, token)
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    Path(doc.file_path).unlink(missing_ok=True)
    await db.delete(doc)


def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        original_name=doc.original_name,
        status=doc.status,
        chunk_count=doc.chunk_count,
        page_count=doc.page_count,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat(),
    )
