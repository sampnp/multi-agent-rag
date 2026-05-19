import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvalResult(Base):
    """One metric score from one evaluation run."""
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # UUID4 grouping
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    contexts: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # list of context strings

    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)  # faithfulness, answer_relevancy, etc.
    score: Mapped[float] = mapped_column(Float, nullable=False)           # 0.0–1.0
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)    # reasoning text, sub-scores
