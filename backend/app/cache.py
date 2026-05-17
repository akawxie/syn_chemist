"""SQLite-backed cache. Wraps slow/deterministic external calls (STOUT, OPSIN, LLM judges)."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, TypeVar

from sqlmodel import select

from .config import settings
from .db import CacheEntry, session

T = TypeVar("T")

# Registry of dataclasses we know how to round-trip through the cache.
# Lazy-imported to avoid import cycles.
def _dataclass_registry() -> dict[str, type]:
    from .llm.base import JudgeResult
    from .pipeline.naming import NormalizedMolecule
    return {"JudgeResult": JudgeResult, "NormalizedMolecule": NormalizedMolecule}


def _encode(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"__dc__": type(value).__name__, **dataclasses.asdict(value)}
    return value


def _decode(value: Any) -> Any:
    if isinstance(value, dict) and "__dc__" in value:
        name = value.pop("__dc__")
        cls = _dataclass_registry().get(name)
        if cls is not None:
            try:
                return cls(**value)
            except Exception:
                return value
    return value


def _hash_key(namespace: str, payload: Any) -> str:
    raw = json.dumps({"ns": namespace, "p": payload}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(namespace: str, payload: Any) -> Any | None:
    key = _hash_key(namespace, payload)
    with session() as s:
        row = s.exec(select(CacheEntry).where(CacheEntry.key == key)).first()
        if row is None:
            return None
        if settings.cache_ttl_seconds > 0:
            age = datetime.utcnow() - row.created_at
            if age > timedelta(seconds=settings.cache_ttl_seconds):
                return None
        return _decode(json.loads(row.value_json))


def cache_set(namespace: str, payload: Any, value: Any) -> None:
    key = _hash_key(namespace, payload)
    with session() as s:
        existing = s.exec(select(CacheEntry).where(CacheEntry.key == key)).first()
        if existing:
            existing.value_json = json.dumps(_encode(value), default=str)
            existing.created_at = datetime.utcnow()
            s.add(existing)
        else:
            s.add(
                CacheEntry(
                    key=key,
                    namespace=namespace,
                    value_json=json.dumps(_encode(value), default=str),
                )
            )
        s.commit()


def cached(namespace: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for async functions. The first positional arg is treated as the cache payload.

    Use on functions where the same input deterministically yields the same output
    (STOUT inference, OPSIN parsing, LLM judging at temperature=0).
    """

    def deco(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            payload = {"args": args[1:] if args else (), "kwargs": kwargs}
            # Skip 'self' if this is a bound method.
            if args and hasattr(args[0], "__class__") and not isinstance(args[0], (str, bytes, int, float, list, dict, tuple)):
                payload = {"args": args[1:], "kwargs": kwargs, "cls": args[0].__class__.__name__}
            else:
                payload = {"args": args, "kwargs": kwargs}
            hit = cache_get(namespace, payload)
            if hit is not None:
                return hit  # type: ignore[return-value]
            result = await fn(*args, **kwargs)
            cache_set(namespace, payload, result)
            return result

        return wrapper

    return deco
