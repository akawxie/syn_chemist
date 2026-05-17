"""Module C — Synthesis Route Recommendation (retrosynthesis)."""
from __future__ import annotations

from ..llm import JudgeProvider, get_judge_provider
from ..pipeline import prompts
from ..pipeline.confidence import composite_confidence
from ..pipeline.naming import RoundTripValidator
from ..pipeline.verify import detect_functional_groups, verify_retro


async def run_retro(
    target: str,
    *,
    judge: JudgeProvider | None = None,
    validator: RoundTripValidator | None = None,
) -> dict:
    judge = judge or get_judge_provider()
    validator = validator or RoundTripValidator()

    n = await validator.normalize(target)
    if not n.canonical_smiles:
        return {
            "module": "retro",
            "error": "Could not parse target.",
            "notes": n.notes,
            "confidence": {"composite": 0.0},
        }

    detected = detect_functional_groups(n.canonical_smiles)
    user = prompts.render(
        "retro.j2",
        smiles=n.canonical_smiles,
        iupac=n.iupac,
        detected_groups=detected,
    )
    system = prompts.render("system.j2")

    judge_result = await judge.judge(system, user)
    routes = judge_result.parsed.get("routes", []) or []

    verify_report = verify_retro(n.canonical_smiles, routes)
    confidence = composite_confidence(
        n.round_trip_score,
        judge_result.self_confidence,
        verify_report.pass_rate,
    )
    return {
        "module": "retro",
        "target": n.__dict__,
        "detected_groups": detected,
        "routes": routes,
        "narrative": judge_result.raw_text,
        "verification": {"pass_rate": verify_report.pass_rate, "checks": verify_report.checks},
        "confidence": confidence.to_dict(),
        "judge": {"provider": judge_result.provider, "model": judge_result.model},
    }
