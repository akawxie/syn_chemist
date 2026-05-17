"""Pytest fixtures: isolated SQLite, fake judge provider."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Force a temp SQLite path before app modules are imported, so the global engine
# in app.db points at the test DB.
_tmp = tempfile.mkdtemp(prefix="ai_chemist_test_")
os.environ["SQLITE_PATH"] = str(Path(_tmp) / "test.db")


@pytest.fixture(autouse=True)
def _isolate_sqlite(monkeypatch, tmp_path):
    """Each test gets its own SQLite file so cache state doesn't leak."""
    from app import config, db

    db_path = tmp_path / "ai_chemist.db"
    monkeypatch.setattr(config.settings, "sqlite_path", db_path)
    # Reset the singleton engine; create_all on first use.
    monkeypatch.setattr(db, "_engine", None)
    yield


class FakeJudge:
    """Deterministic in-process JudgeProvider for tests."""

    name = "fake"

    def __init__(self, payload: dict, self_confidence: float = 0.7) -> None:
        self.payload = payload
        self._sc = self_confidence

    async def judge(self, system: str, user: str):
        from app.llm.base import JudgeResult

        return JudgeResult(
            raw_text="<fake>",
            parsed=self.payload,
            self_confidence=self._sc,
            provider="fake",
            model="fake-1",
        )


@pytest.fixture
def fake_judge_factory():
    return FakeJudge
