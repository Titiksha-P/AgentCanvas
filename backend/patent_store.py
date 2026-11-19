"""SQLAlchemy-backed patent evaluation history (SQLite local; PostgreSQL via DATABASE_URL)."""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentcanvas_patent.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class EvaluationRecord(Base):
    __tablename__ = "patent_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_type: Mapped[str] = mapped_column(String(32), index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), default="0.2.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    summary_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)

def init_db() -> None:
    # Production schemas are managed by committed SQL migrations. Avoid
    # implicit DDL at request time; local/test SQLite keeps create_all.
    if os.getenv("APP_ENV", "").lower() != "production":
        Base.metadata.create_all(bind=engine)

def save_evaluation(evaluation_type: str, summary: dict, result: dict) -> int:
    init_db()
    with SessionLocal() as session:
        record = EvaluationRecord(evaluation_type=evaluation_type,
                                  summary_json=json.dumps(summary, ensure_ascii=False),
                                  result_json=json.dumps(result, ensure_ascii=False))
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id

def list_evaluations(limit: int = 25) -> list[dict]:
    init_db()
    with SessionLocal() as session:
        rows = session.scalars(select(EvaluationRecord).order_by(EvaluationRecord.created_at.desc()).limit(limit)).all()
        return [{"id": row.id, "type": row.evaluation_type, "dataset_version": row.dataset_version,
                 "created_at": row.created_at.isoformat(), "summary": json.loads(row.summary_json),
                 "result": json.loads(row.result_json)} for row in rows]
