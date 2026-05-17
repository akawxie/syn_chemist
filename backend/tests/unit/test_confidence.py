"""Unit tests for composite confidence scoring."""
from __future__ import annotations

from app.pipeline.confidence import composite_confidence


def test_endpoints():
    assert composite_confidence(0, 0, 0).composite == 0.0
    assert composite_confidence(1, 1, 1).composite == 1.0


def test_clamps_inputs():
    c = composite_confidence(2.0, -0.5, 0.5)
    assert 0 <= c.composite <= 1
    assert c.round_trip == 1.0
    assert c.judge == 0.0


def test_monotonic_in_each_component():
    base = composite_confidence(0.5, 0.5, 0.5).composite
    assert composite_confidence(0.9, 0.5, 0.5).composite >= base
    assert composite_confidence(0.5, 0.9, 0.5).composite >= base
    assert composite_confidence(0.5, 0.5, 0.9).composite >= base


def test_breakdown_keys():
    out = composite_confidence(0.8, 0.6, 0.7).to_dict()
    assert {"round_trip", "judge", "verify", "composite", "weights"} <= set(out.keys())
    assert {"round_trip", "judge", "verify"} == set(out["weights"].keys())
