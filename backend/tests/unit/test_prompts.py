"""Snapshot-style tests for prompt rendering."""
from __future__ import annotations

from app.pipeline import prompts


def test_system_prompt_renders():
    s = prompts.render("system.j2")
    assert "JUDGE" in s
    assert "STRICT JSON" in s


def test_fga_prompt_includes_smiles_and_groups():
    out = prompts.render(
        "fga.j2",
        smiles="CCO",
        iupac="ethanol",
        detected_groups=[{"name": "alcohol", "severity": "low", "count": 1}],
    )
    assert "CCO" in out
    assert "ethanol" in out
    assert "alcohol" in out
    assert "self_confidence" in out


def test_fga_prompt_handles_no_iupac():
    out = prompts.render(
        "fga.j2",
        smiles="CCO",
        iupac=None,
        detected_groups=[],
    )
    assert "CCO" in out
    assert "IUPAC:" not in out  # block skipped


def test_conditions_prompt_includes_both_molecules():
    out = prompts.render(
        "conditions.j2",
        reactant="Brc1ccccc1",
        reactant_iupac=None,
        product="OB(O)c1ccccc1",
        product_iupac=None,
        reaction_class_hint="Suzuki coupling",
    )
    assert "Brc1ccccc1" in out
    assert "OB(O)c1ccccc1" in out
    assert "Suzuki" in out


def test_retro_prompt_renders():
    out = prompts.render(
        "retro.j2",
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        iupac="2-acetoxybenzoic acid",
        detected_groups=[],
    )
    assert "routes" in out
    assert "2-acetoxybenzoic acid" in out
