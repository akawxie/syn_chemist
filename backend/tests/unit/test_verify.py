"""Unit tests for RDKit verification helpers."""
from __future__ import annotations

from app.pipeline.verify import (
    atom_counts,
    detect_functional_groups,
    is_valid_smiles,
    reaction_atom_balance,
    verify_conditions,
    verify_fga,
    verify_retro,
)


def test_is_valid_smiles():
    assert is_valid_smiles("CCO")
    assert is_valid_smiles("CC(=O)Oc1ccccc1C(=O)O")
    assert not is_valid_smiles("not_a_smiles")
    assert not is_valid_smiles("")


def test_detect_functional_groups_aspirin():
    hits = {h["name"] for h in detect_functional_groups("CC(=O)Oc1ccccc1C(=O)O")}
    assert "ester" in hits
    assert "carboxylic_acid" in hits


def test_detect_functional_groups_nitro_high_severity():
    hits = detect_functional_groups("[O-][N+](=O)c1ccccc1")
    nitro = next((h for h in hits if h["name"] == "nitro"), None)
    assert nitro is not None
    assert nitro["severity"] == "high"


def test_detect_functional_groups_epoxide():
    hits = {h["name"] for h in detect_functional_groups("C1OC1")}
    assert "epoxide" in hits


def test_atom_counts():
    c = atom_counts("CCO")
    assert c["C"] == 2
    assert c["O"] == 1
    assert c["H"] == 6  # explicit Hs added


def test_reaction_atom_balance_balanced():
    # CH3CH2OH + CH3COOH -> CH3COOCH2CH3 + H2O  (atom-balanced overall)
    ok, _ = reaction_atom_balance(
        ["CCO", "CC(=O)O"],
        ["CCOC(=O)C", "O"],
    )
    assert ok


def test_reaction_atom_balance_unbalanced():
    ok, detail = reaction_atom_balance(["CCO"], ["CCC"])
    assert not ok
    assert "unbalanced" in detail


def test_verify_fga_pass_when_alert_matches():
    # nitrobenzene; LLM correctly flags 'nitro'
    rep = verify_fga(
        "[O-][N+](=O)c1ccccc1",
        [{"group": "nitro", "severity": "high", "risk": "explosive"}],
    )
    assert rep.pass_rate == 1.0


def test_verify_fga_fail_when_alert_invented():
    rep = verify_fga(
        "CCO",
        [{"group": "azide", "severity": "high", "risk": "explosive"}],
    )
    # structure_legality passes, the alert check fails -> 0.5
    assert 0 < rep.pass_rate < 1.0


def test_verify_conditions_completeness():
    rep = verify_conditions(
        "Brc1ccccc1",  # bromobenzene
        "OB(O)c1ccccc1",  # phenylboronic acid (silly product, just structural)
        [
            {"solvent": "THF", "temperature": "65 C"},
            {"solvent": "", "temperature": None},  # incomplete
        ],
    )
    completeness = [c for c in rep.checks if c["name"].startswith("candidate_")]
    assert any(c["ok"] for c in completeness)
    assert any(not c["ok"] for c in completeness)


def test_verify_retro_step_legality():
    rep = verify_retro(
        "CC(=O)Oc1ccccc1C(=O)O",
        [
            {
                "name": "via salicylic acid",
                "steps": [
                    {"step": 1, "intermediate_smiles": "Oc1ccccc1C(=O)O"},
                    {"step": 2, "intermediate_smiles": "garbage"},
                ],
            }
        ],
    )
    legal = [c for c in rep.checks if "step" in c["name"]]
    assert any(c["ok"] for c in legal)
    assert any(not c["ok"] for c in legal)
