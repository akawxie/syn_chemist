"""P3 — lang propagates through prompts and cache key."""
from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class _Recorded:
    system: str
    user: str


class _RecordingJudge:
    name = "rec"

    def __init__(self) -> None:
        self.calls: list[_Recorded] = []
        self.payload = {"alerts": [], "overall_self_confidence": 0.5}

    async def judge(self, system: str, user: str):
        from app.llm.base import JudgeResult

        self.calls.append(_Recorded(system, user))
        return JudgeResult(
            raw_text='{"alerts": []}', parsed=self.payload,
            self_confidence=0.5, provider="rec", model="m",
        )


@pytest.mark.asyncio
async def test_fga_lang_en_no_directive():
    from app.modules.fga import run_fga
    from app.pipeline.naming import NormalizedMolecule

    class FakeValidator:
        async def normalize(self, raw):
            return NormalizedMolecule(
                input_raw=raw, canonical_smiles="CCO", iupac="ethanol",
                round_trip_ok=True, round_trip_score=1.0, notes=[],
            )

    judge = _RecordingJudge()
    out = await run_fga("CCO", judge=judge, validator=FakeValidator(), lang="en")
    assert out["output_language"] == "en"
    # No language directive emitted when EN (the default)
    assert "Respond in" not in judge.calls[0].system


@pytest.mark.asyncio
async def test_fga_lang_zh_emits_directive():
    from app.modules.fga import run_fga
    from app.pipeline.naming import NormalizedMolecule

    class FakeValidator:
        async def normalize(self, raw):
            return NormalizedMolecule(
                input_raw=raw, canonical_smiles="CCO", iupac="ethanol",
                round_trip_ok=True, round_trip_score=1.0, notes=[],
            )

    judge = _RecordingJudge()
    out = await run_fga("CCO", judge=judge, validator=FakeValidator(), lang="zh")
    assert out["output_language"] == "zh"
    sys_prompt = judge.calls[0].system
    assert "Respond in" in sys_prompt
    assert "Chinese" in sys_prompt
    # And critically — preservation rule for identifiers
    assert "SMILES" in sys_prompt
    assert "do not translate" in sys_prompt


@pytest.mark.asyncio
async def test_cache_lang_separation(monkeypatch):
    """Different lang must hit different cache entries."""
    from app.cache import cache_get, cache_set

    cache_set("test:lang", {"q": "x", "lang": "en"}, "english-result")
    cache_set("test:lang", {"q": "x", "lang": "zh"}, "chinese-result")
    assert cache_get("test:lang", {"q": "x", "lang": "en"}) == "english-result"
    assert cache_get("test:lang", {"q": "x", "lang": "zh"}) == "chinese-result"


def test_invalid_lang_rejected():
    """API schema rejects lang values outside the Literal."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import fga as fga_api

    app = FastAPI()
    app.include_router(fga_api.router)
    c = TestClient(app)
    r = c.post("/api/fga", json={"input": "CCO", "lang": "fr"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_lang_helpers():
    from app.i18n import lang_name

    assert lang_name("en") is None
    assert lang_name(None) is None
    assert "Chinese" in (lang_name("zh") or "")
