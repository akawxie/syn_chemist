"""Composite confidence: round-trip score + LLM self-confidence + RDKit verifier pass-rate."""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings


@dataclass
class ConfidenceBreakdown:
    round_trip: float
    judge: float
    verify: float
    composite: float

    def to_dict(self) -> dict:
        return {
            "round_trip": round(self.round_trip, 3),
            "judge": round(self.judge, 3),
            "verify": round(self.verify, 3),
            "composite": round(self.composite, 3),
            "weights": {
                "round_trip": settings.confidence_weight_round_trip,
                "judge": settings.confidence_weight_judge,
                "verify": settings.confidence_weight_verify,
            },
        }


def composite_confidence(
    round_trip: float,
    judge_self_confidence: float,
    verify_pass_rate: float,
) -> ConfidenceBreakdown:
    """Weighted average with weights from settings.

    Monotonic in each input: increasing any component (with others held constant)
    cannot decrease the composite. Tested in unit tests.
    """
    rt = max(0.0, min(1.0, round_trip))
    j = max(0.0, min(1.0, judge_self_confidence))
    v = max(0.0, min(1.0, verify_pass_rate))
    composite = (
        settings.confidence_weight_round_trip * rt
        + settings.confidence_weight_judge * j
        + settings.confidence_weight_verify * v
    )
    total_weight = (
        settings.confidence_weight_round_trip
        + settings.confidence_weight_judge
        + settings.confidence_weight_verify
    )
    if total_weight > 0:
        composite = composite / total_weight
    return ConfidenceBreakdown(round_trip=rt, judge=j, verify=v, composite=composite)
