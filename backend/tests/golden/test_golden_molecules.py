"""Golden molecule set — known FGA detections from RDKit SMARTS (no LLM, no network).

These tests pin the SMARTS library so future edits can't silently regress detection.
"""
from __future__ import annotations

import pytest

from app.pipeline.verify import detect_functional_groups, is_valid_smiles

GOLDEN = [
    # (name, SMILES, expected_groups (subset))
    ("aspirin", "CC(=O)Oc1ccccc1C(=O)O", {"ester", "carboxylic_acid"}),
    ("ibuprofen", "CC(C)Cc1ccc(C(C)C(=O)O)cc1", {"carboxylic_acid"}),
    ("paracetamol", "CC(=O)Nc1ccc(O)cc1", {"amide", "phenol"}),
    ("acetamide", "CC(=O)N", {"amide"}),
    ("nitrobenzene", "[O-][N+](=O)c1ccccc1", {"nitro"}),
    ("phenylazide", "[N-]=[N+]=Nc1ccccc1", {"azide"}),
    ("benzaldehyde", "O=Cc1ccccc1", {"aldehyde"}),
    ("acetone", "CC(=O)C", {"ketone"}),
    ("ethanol", "CCO", {"alcohol"}),
    ("phenol", "Oc1ccccc1", {"phenol"}),
    ("phenylboronic_acid", "OB(O)c1ccccc1", {"boronic_acid"}),
    ("bromobenzene", "Brc1ccccc1", {"aryl_halide"}),
    ("ethylene_oxide", "C1CO1", {"epoxide"}),
    ("benzoyl_chloride", "O=C(Cl)c1ccccc1", {"acyl_chloride"}),
    ("phenyl_isocyanate", "O=C=Nc1ccccc1", {"isocyanate"}),
]


@pytest.mark.parametrize("name,smiles,expected", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_fga_detection(name, smiles, expected):
    assert is_valid_smiles(smiles), f"{name}: invalid SMILES"
    detected = {h["name"] for h in detect_functional_groups(smiles)}
    missing = expected - detected
    assert not missing, f"{name}: expected {expected}, missing {missing} (got {detected})"
