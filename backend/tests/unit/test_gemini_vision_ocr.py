"""P2 — Gemini vision OCR response parser (no network)."""
from __future__ import annotations

import pytest

from app.llm.gemini_vision import (
    NotAMoleculeError,
    OCRResult,
    parse_ocr_response,
)


def test_ocr_clean_smiles():
    out = parse_ocr_response("CCO")
    assert out.smiles == "CCO"
    assert out.warning is None


def test_ocr_smiles_with_fences():
    out = parse_ocr_response("```smiles\nCCO\n```")
    assert out.smiles == "CCO"


def test_ocr_smiles_with_bare_fences():
    out = parse_ocr_response("```\nCCO\n```")
    assert out.smiles == "CCO"


def test_ocr_smiles_with_quotes():
    out = parse_ocr_response('"CCO"')
    assert out.smiles == "CCO"


def test_ocr_smiles_with_prefix():
    out = parse_ocr_response("SMILES: CCO")
    assert out.smiles == "CCO"


def test_ocr_not_molecule():
    with pytest.raises(NotAMoleculeError):
        parse_ocr_response("NOT_A_MOLECULE")


def test_ocr_uncertain():
    out = parse_ocr_response("UNCERTAIN")
    assert out.smiles == ""
    assert "uncertain" in (out.warning or "").lower()


def test_ocr_invalid_smiles():
    out = parse_ocr_response("XXX@@@")
    assert out.smiles == ""
    assert "invalid SMILES" in (out.warning or "")


def test_ocr_garbage_with_prose():
    """If the model rambles, RDKit can't validate, so we surface as invalid."""
    out = parse_ocr_response("I see a molecule with several rings...")
    assert out.smiles == ""
    assert out.warning is not None


def test_ocr_empty():
    out = parse_ocr_response("")
    assert out.smiles == ""
    assert "empty" in (out.warning or "").lower()


def test_ocr_real_chemistry():
    """Various canonical SMILES should pass through cleanly."""
    for smi in ["CCO", "CC(=O)O", "c1ccccc1", "CC(=O)Oc1ccccc1C(=O)O"]:
        out = parse_ocr_response(smi)
        assert out.smiles == smi, f"failed for {smi}"
        assert out.warning is None
