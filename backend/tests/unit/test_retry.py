"""P1 — retry behaviour for HTTP providers + LLM JSON reprompt."""
from __future__ import annotations

import httpx
import pytest

from app.llm._retry import is_retryable_exception, with_retry
from app.llm.base import JudgeResult, try_parse_or_reprompt

# ---------- with_retry primitive ----------


@pytest.mark.asyncio
async def test_with_retry_first_try_success():
    calls = {"n": 0}

    async def ok():
        calls["n"] += 1
        return "ok"

    result, retries = await with_retry(ok)
    assert result == "ok"
    assert retries == 0
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_recovers_after_one_failure():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        return "ok"

    result, retries = await with_retry(flaky, base_delay=0.01, max_delay=0.05)
    assert result == "ok"
    assert retries == 1
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_with_retry_exhausts_attempts():
    calls = {"n": 0}

    async def always_fail():
        calls["n"] += 1
        raise httpx.ConnectError("nope")

    with pytest.raises(httpx.ConnectError):
        await with_retry(always_fail, base_delay=0.01, max_delay=0.05)
    assert calls["n"] == 3  # default max_attempts=3


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_non_retryable():
    """A ValueError (no status_code, not in known-retryable set) must surface immediately."""
    calls = {"n": 0}

    async def bad():
        calls["n"] += 1
        raise ValueError("client bug")

    with pytest.raises(ValueError):
        await with_retry(bad, base_delay=0.01)
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_401():
    """Auth errors shouldn't waste retries — 4xx (≠429) is fatal."""
    calls = {"n": 0}

    class FakeAuthError(Exception):
        status_code = 401

    async def auth_fail():
        calls["n"] += 1
        raise FakeAuthError("bad key")

    with pytest.raises(FakeAuthError):
        await with_retry(auth_fail, base_delay=0.01)
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_with_retry_retries_on_429():
    calls = {"n": 0}

    class FakeRateLimit(Exception):
        status_code = 429

    async def rate_limited():
        calls["n"] += 1
        if calls["n"] < 2:
            raise FakeRateLimit("slow down")
        return "ok"

    result, retries = await with_retry(rate_limited, base_delay=0.01)
    assert result == "ok"
    assert retries == 1


@pytest.mark.asyncio
async def test_with_retry_retries_on_500():
    calls = {"n": 0}

    class FakeServerError(Exception):
        status_code = 503

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise FakeServerError("upstream")
        return "ok"

    result, retries = await with_retry(flaky, base_delay=0.01)
    assert result == "ok"
    assert retries == 2


# ---------- is_retryable_exception ----------


def test_is_retryable_httpx():
    assert is_retryable_exception(httpx.ConnectError("x"))
    assert is_retryable_exception(httpx.ReadTimeout("x"))


def test_is_retryable_named():
    class RateLimitError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    assert is_retryable_exception(RateLimitError())
    assert is_retryable_exception(APIConnectionError())


def test_not_retryable_value_error():
    assert not is_retryable_exception(ValueError("nope"))


def test_not_retryable_4xx():
    class BadRequest(Exception):
        status_code = 400

    assert not is_retryable_exception(BadRequest())


# ---------- try_parse_or_reprompt ----------


class _RecordingJudge:
    """Test double that returns canned results per call and records system prompts."""

    name = "rec"

    def __init__(self, results: list[JudgeResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, str]] = []
        self._i = 0

    async def judge(self, system: str, user: str) -> JudgeResult:
        self.calls.append((system, user))
        r = self.results[self._i]
        self._i += 1
        return r


@pytest.mark.asyncio
async def test_reprompt_skipped_when_parsed_ok():
    good = JudgeResult(
        raw_text='{"x": 1}', parsed={"x": 1}, self_confidence=0.8,
        provider="rec", model="m",
    )
    judge = _RecordingJudge([good])
    out = await try_parse_or_reprompt(judge, "sys", "user")
    assert out.parsed == {"x": 1}
    assert out.json_retry is False
    assert len(judge.calls) == 1


@pytest.mark.asyncio
async def test_reprompt_recovers_on_second_try():
    bad = JudgeResult(
        raw_text="here is what you want: maybe", parsed={},
        self_confidence=0.5, provider="rec", model="m",
    )
    good = JudgeResult(
        raw_text='{"x": 1}', parsed={"x": 1},
        self_confidence=0.7, provider="rec", model="m",
    )
    judge = _RecordingJudge([bad, good])
    out = await try_parse_or_reprompt(judge, "sys", "user")
    assert out.parsed == {"x": 1}
    assert out.json_retry is True
    assert len(judge.calls) == 2
    # Second call must have the stricter suffix appended.
    assert "Return ONLY the JSON object" in judge.calls[1][0]


@pytest.mark.asyncio
async def test_reprompt_returns_failure_after_second_fail():
    bad1 = JudgeResult(
        raw_text="garbage 1", parsed={},
        self_confidence=0.5, provider="rec", model="m",
    )
    bad2 = JudgeResult(
        raw_text="garbage 2", parsed={},
        self_confidence=0.5, provider="rec", model="m",
    )
    judge = _RecordingJudge([bad1, bad2])
    out = await try_parse_or_reprompt(judge, "sys", "user")
    assert out.parsed == {}
    assert out.json_retry is True
    assert out.raw_text == "garbage 2"  # latest raw_text preserved
    assert len(judge.calls) == 2


@pytest.mark.asyncio
async def test_reprompt_skipped_when_raw_text_empty():
    """If LLM returned nothing at all, no point reprompting."""
    empty = JudgeResult(
        raw_text="", parsed={}, self_confidence=0.0, provider="rec", model="m",
    )
    judge = _RecordingJudge([empty])
    out = await try_parse_or_reprompt(judge, "sys", "user")
    assert len(judge.calls) == 1
    assert out.json_retry is False


# ---------- naming providers retry on 5xx ----------


@pytest.mark.asyncio
async def test_pubchem_retries_then_succeeds(monkeypatch):
    """Mock httpx to fail twice then succeed; PubChem provider should return IUPAC."""
    from app.pipeline.naming import PubChemIUPACProvider

    calls = {"n": 0}

    class FakeResp:
        def __init__(self, status: int, text: str = ""):
            self.status_code = status
            self.text = text
            self.request = httpx.Request("GET", "https://x")

    class FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url):
            calls["n"] += 1
            if calls["n"] < 3:
                return FakeResp(503)
            return FakeResp(200, "2-acetoxybenzoic acid\n")

    monkeypatch.setattr("app.pipeline.naming.httpx.AsyncClient", FakeClient)
    # also speed up sleeps
    monkeypatch.setattr("app.llm._retry.asyncio.sleep", _instant_sleep)

    p = PubChemIUPACProvider()
    name = await p.to_iupac("CC(=O)Oc1ccccc1C(=O)O")
    assert name == "2-acetoxybenzoic acid"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_pubchem_404_no_retry(monkeypatch):
    from app.pipeline.naming import PubChemIUPACProvider

    calls = {"n": 0}

    class FakeResp:
        def __init__(self, status: int):
            self.status_code = status
            self.text = ""
            self.request = httpx.Request("GET", "https://x")

    class FakeClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url):
            calls["n"] += 1
            return FakeResp(404)

    monkeypatch.setattr("app.pipeline.naming.httpx.AsyncClient", FakeClient)
    p = PubChemIUPACProvider()
    name = await p.to_iupac("XYZ")
    assert name is None
    assert calls["n"] == 1  # no retry on 404


async def _instant_sleep(_):
    return None
