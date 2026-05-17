"""JSON extraction in JudgeProvider helper."""
from __future__ import annotations

from app.llm.base import JudgeProvider


def test_extract_json_clean():
    out = JudgeProvider.extract_json('{"a": 1, "b": "x"}')
    assert out == {"a": 1, "b": "x"}


def test_extract_json_fenced():
    out = JudgeProvider.extract_json('```json\n{"a": 1}\n```')
    assert out == {"a": 1}


def test_extract_json_with_prose():
    out = JudgeProvider.extract_json('Sure! Here you go:\n{"a": 1, "b": [1,2]}\nLet me know.')
    assert out == {"a": 1, "b": [1, 2]}


def test_extract_json_garbage_returns_empty():
    assert JudgeProvider.extract_json("totally not json") == {}
    assert JudgeProvider.extract_json("") == {}


def test_confidence_default():
    assert JudgeProvider.confidence_from({}, default=0.5) == 0.5
    assert JudgeProvider.confidence_from({"overall_self_confidence": 0.8}) == 0.8
    assert JudgeProvider.confidence_from({"overall_self_confidence": 2.0}) == 1.0
    assert JudgeProvider.confidence_from({"overall_self_confidence": -1}) == 0.0
