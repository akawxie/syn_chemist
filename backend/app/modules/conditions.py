"""Module B — Reaction Condition Recommendation."""
from __future__ import annotations

from ..llm import JudgeProvider, get_judge_provider
from ..pipeline import prompts
from ..pipeline.confidence import composite_confidence
from ..pipeline.naming import RoundTripValidator
from ..pipeline.verify import verify_conditions


async def run_conditions(
    reactant: str,
    product: str,
    *,
    reagent: str | None = None,
    reaction_class_hint: str | None = None,
    judge: JudgeProvider | None = None,
    validator: RoundTripValidator | None = None,
) -> dict:
    judge = judge or get_judge_provider()
    validator = validator or RoundTripValidator()

    n_react = await validator.normalize(reactant)
    n_prod = await validator.normalize(product)
    if not n_react.canonical_smiles or not n_prod.canonical_smiles:
        return {
            "module": "conditions",
            "error": "Could not parse reactant or product.",
            "reactant_notes": n_react.notes,
            "product_notes": n_prod.notes,
            "confidence": {"composite": 0.0},
        }

    n_reagent = await validator.normalize(reagent) if reagent else None

    user = prompts.render(
        "conditions.j2",
        reactant=n_react.canonical_smiles,
        reactant_iupac=n_react.iupac,
        product=n_prod.canonical_smiles,
        product_iupac=n_prod.iupac,
        reagent=n_reagent.canonical_smiles if n_reagent else None,
        reagent_iupac=n_reagent.iupac if n_reagent else None,
        reaction_class_hint=reaction_class_hint,
    )
    system = prompts.render("system.j2")

    judge_result = await judge.judge(system, user)
    candidates = judge_result.parsed.get("candidates", []) or []
    reaction_class_guess = judge_result.parsed.get("reaction_class_guess")

    verify_report = verify_conditions(n_react.canonical_smiles, n_prod.canonical_smiles, candidates)
    avg_round_trip = (n_react.round_trip_score + n_prod.round_trip_score) / 2
    confidence = composite_confidence(
        avg_round_trip,
        judge_result.self_confidence,
        verify_report.pass_rate,
    )
    return {
        "module": "conditions",
        "reactant": n_react.__dict__,
        "product": n_prod.__dict__,
        "reagent": n_reagent.__dict__ if n_reagent else None,
        "reaction_class_guess": reaction_class_guess,
        "candidates": candidates,
        "narrative": judge_result.raw_text,
        "verification": {"pass_rate": verify_report.pass_rate, "checks": verify_report.checks},
        "confidence": confidence.to_dict(),
        "judge": {"provider": judge_result.provider, "model": judge_result.model},
    }
