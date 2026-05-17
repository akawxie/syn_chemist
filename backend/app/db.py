"""SQLite via sqlmodel. One file in the container; cache + simple query log."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Field, Session, SQLModel, create_engine

from .config import settings


class CacheEntry(SQLModel, table=True):
    __tablename__ = "cache_entry"
    key: str = Field(primary_key=True)  # sha256(namespace + payload)
    namespace: str = Field(index=True)  # 'stout' | 'opsin' | 'judge:<provider>:<model>'
    value_json: str  # serialized response
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class QueryLog(SQLModel, table=True):
    __tablename__ = "query_log"
    id: int | None = Field(default=None, primary_key=True)
    module: str = Field(index=True)  # 'fga' | 'conditions' | 'retro' | 'normalize'
    input_summary: str
    confidence: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


_engine: Any = None


def get_engine():
    global _engine
    if _engine is None:
        url = f"sqlite:///{settings.sqlite_path}"
        _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine


def session() -> Session:
    return Session(get_engine())
