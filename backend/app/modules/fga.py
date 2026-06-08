"""Module A — Functional Group Alert."""
from __future__ import annotations

from ..i18n import Lang, lang_name
from ..llm import JudgeProvider, get_judge_provider
from ..llm.base import try_parse_or_reprompt
from ..pipeline import prompts
from ..pipeline.confidence import composite_confidence
from ..pipeline.naming import NormalizedMolecule, RoundTripValidator
from ..pipeline.verify import detect_fragments, detect_functional_groups, verify_fga


async def run_fga(
    raw_input: str,
    *,
    judge: JudgeProvider | None = None,
    validator: RoundTripValidator | None = None,
    lang: Lang = "en",
) -> dict:
    judge = judge or get_judge_provider()
    validator = validator or RoundTripValidator()

    normalized: NormalizedMolecule = await validator.normalize(raw_input)
    if not normalized.canonical_smiles:
        return _bad_input_response(normalized)

    detected = detect_functional_groups(normalized.canonical_smiles)
    fragments = detect_fragments(normalized.canonical_smiles)
    user = prompts.render(
        "fga.j2",
        smiles=normalized.canonical_smiles,
        iupac=normalized.iupac,
        detected_groups=detected,
        fragments=fragments,
    )
    system = prompts.render("system.j2", output_language_name=lang_name(lang))

    judge_result = await try_parse_or_reprompt(judge, system, user)
    alerts = judge_result.parsed.get("alerts", []) or []

    verify_report = verify_fga(normalized.canonical_smiles, alerts)
    confidence = composite_confidence(
        normalized.round_trip_score,
        judge_result.self_confidence,
        verify_report.pass_rate,
    )
    return {
        "module": "fga",
        "input": raw_input,
        "normalized": normalized.__dict__,
        "detected_groups": detected,
        "fragments": fragments,
        "alerts": alerts,
        "narrative": judge_result.raw_text,
        "verification": {"pass_rate": verify_report.pass_rate, "checks": verify_report.checks},
        "confidence": confidence.to_dict(),
        "judge": {
            "provider": judge_result.provider,
            "model": judge_result.model,
            "retry_count": judge_result.retry_count,
            "json_retry": judge_result.json_retry,
        },
        "output_language": lang,
    }


def _bad_input_response(n: NormalizedMolecule) -> dict:
    return {
        "module": "fga",
        "input": n.input_raw,
        "error": "Could not parse molecule input.",
        "notes": n.notes,
        "confidence": {"composite": 0.0},
    }
