"""Integration tests: real RDKit, mocked LLM via FakeJudge, naming providers stubbed."""
from __future__ import annotations

import pytest

from app.modules.conditions import run_conditions
from app.modules.fga import run_fga
from app.modules.retro import run_retro
from app.pipeline.naming import RoundTripValidator


class _StubIUPAC:
    async def to_iupac(self, smiles: str) -> str | None:
        return None  # skip naming round-trip in integration tests


class _StubOPSIN:
    async def to_smiles(self, iupac: str) -> str | None:
        return None


def _validator() -> RoundTripValidator:
    return RoundTripValidator(_StubIUPAC(), _StubOPSIN())


@pytest.mark.asyncio
async def test_fga_aspirin_full_pipeline(fake_judge_factory):
    fake = fake_judge_factory(
        {
            "alerts": [
                {"group": "ester", "severity": "low", "risk": "hydrolysis sensitive", "self_confidence": 0.8},
                {"group": "carboxylic_acid", "severity": "low", "risk": "metal coord", "self_confidence": 0.8},
            ],
            "overall_self_confidence": 0.8,
        }
    )
    out = await run_fga("CC(=O)Oc1ccccc1C(=O)O", judge=fake, validator=_validator())
    assert out["module"] == "fga"
    assert "ester" in {h["name"] for h in out["detected_groups"]}
    assert out["confidence"]["composite"] > 0.4
    assert out["verification"]["pass_rate"] == 1.0
    assert out["judge"]["provider"] == "fake"


@pytest.mark.asyncio
async def test_fga_invented_alert_lowers_confidence(fake_judge_factory):
    fake = fake_judge_factory(
        {
            "alerts": [{"group": "azide", "severity": "high", "risk": "explosion", "self_confidence": 0.9}],
            "overall_self_confidence": 0.9,
        }
    )
    out = await run_fga("CCO", judge=fake, validator=_validator())
    # ethanol has no azide; verify_pass_rate should drop the composite below judge conf.
    assert out["verification"]["pass_rate"] < 1.0
    assert out["confidence"]["composite"] < 0.9


@pytest.mark.asyncio
async def test_conditions_pipeline(fake_judge_factory):
    fake = fake_judge_factory(
        {
            "reaction_class_guess": "Suzuki coupling",
            "candidates": [
                {
                    "solvent": "THF/H2O",
                    "catalyst": "Pd(PPh3)4",
                    "base_or_additive": "K2CO3",
                    "temperature": "80 C",
                    "time": "12 h",
                    "equivalents": {"reactant": 1.0, "boronic_acid": 1.2},
                    "rationale": "standard Suzuki",
                    "self_confidence": 0.8,
                }
            ],
            "overall_self_confidence": 0.8,
        }
    )
    out = await run_conditions(
        "Brc1ccccc1",
        "c1ccc(-c2ccccc2)cc1",  # biphenyl
        judge=fake,
        validator=_validator(),
    )
    assert out["module"] == "conditions"
    assert out["reaction_class_guess"] == "Suzuki coupling"
    assert len(out["candidates"]) == 1
    assert out["confidence"]["composite"] > 0


@pytest.mark.asyncio
async def test_retro_pipeline(fake_judge_factory):
    fake = fake_judge_factory(
        {
            "routes": [
                {
                    "name": "via salicylic acid",
                    "steps": [
                        {
                            "step": 1,
                            "transform": "O-acetylation",
                            "intermediate_smiles": "Oc1ccccc1C(=O)O",
                            "rationale": "deprotect acetate",
                            "self_confidence": 0.9,
                        }
                    ],
                    "self_confidence": 0.9,
                }
            ],
            "overall_self_confidence": 0.85,
        }
    )
    out = await run_retro("CC(=O)Oc1ccccc1C(=O)O", judge=fake, validator=_validator())
    assert out["module"] == "retro"
    assert len(out["routes"]) == 1
    # All step SMILES are valid -> high verify pass rate.
    assert out["verification"]["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_retro_invalid_intermediate_caught(fake_judge_factory):
    fake = fake_judge_factory(
        {
            "routes": [
                {
                    "name": "broken",
                    "steps": [{"step": 1, "intermediate_smiles": "not_a_smiles"}],
                }
            ],
            "overall_self_confidence": 0.9,
        }
    )
    out = await run_retro("CCO", judge=fake, validator=_validator())
    assert out["verification"]["pass_rate"] < 1.0


@pytest.mark.asyncio
async def test_invalid_input_short_circuits(fake_judge_factory):
    fake = fake_judge_factory({})
    out = await run_fga("not a molecule", judge=fake, validator=_validator())
    assert "error" in out
    assert out["confidence"]["composite"] == 0.0
