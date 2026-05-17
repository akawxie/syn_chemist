"""Unit tests for naming pipeline (RDKit canonicalization + round-trip logic)."""
from __future__ import annotations

import pytest

from app.pipeline.naming import (
    NormalizedMolecule,
    RoundTripValidator,
    smiles_equiv,
    to_canonical_smiles,
)


def test_canonical_smiles_basic():
    # Aspirin written two equivalent ways canonicalizes identically.
    a = to_canonical_smiles("CC(=O)Oc1ccccc1C(=O)O")
    b = to_canonical_smiles("O=C(C)Oc1ccccc1C(=O)O")
    assert a is not None and a == b


def test_canonical_smiles_inchi_input():
    inchi = "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
    s = to_canonical_smiles(inchi)
    assert s is not None
    assert "C(=O)O" in s or "OC(=O)" in s  # carboxylic-acid pattern present


def test_invalid_input_returns_none():
    assert to_canonical_smiles("not a molecule") is None
    assert to_canonical_smiles("") is None


def test_smiles_equiv_canonicalizes():
    # Different stringification, same molecule.
    assert smiles_equiv("CC(=O)Oc1ccccc1C(=O)O", "O=C(C)Oc1ccccc1C(=O)O")
    assert not smiles_equiv("CCO", "CCC")


# ---- Round-trip validator with mocked providers ----


class _FakeIUPAC:
    def __init__(self, mapping: dict[str, str | None]) -> None:
        self.mapping = mapping

    async def to_iupac(self, smiles: str) -> str | None:
        return self.mapping.get(smiles)


class _FakeOPSIN:
    def __init__(self, mapping: dict[str, str | None]) -> None:
        self.mapping = mapping

    async def to_smiles(self, iupac: str) -> str | None:
        return self.mapping.get(iupac)


@pytest.mark.asyncio
async def test_round_trip_success():
    canon = to_canonical_smiles("CCO")
    iupac = "ethanol"
    v = RoundTripValidator(
        iupac_provider=_FakeIUPAC({canon: iupac}),
        opsin_provider=_FakeOPSIN({iupac: "OCC"}),  # different string, same canonical
    )
    out = await v.normalize("CCO")
    assert isinstance(out, NormalizedMolecule)
    assert out.round_trip_ok
    assert out.round_trip_score == 1.0
    assert out.iupac == "ethanol"


@pytest.mark.asyncio
async def test_round_trip_mismatch_flagged():
    canon = to_canonical_smiles("CCO")
    v = RoundTripValidator(
        iupac_provider=_FakeIUPAC({canon: "methanol"}),  # wrong name on purpose
        opsin_provider=_FakeOPSIN({"methanol": "CO"}),
    )
    out = await v.normalize("CCO")
    assert not out.round_trip_ok
    assert out.round_trip_score < 1.0
    assert any("mismatch" in n.lower() for n in out.notes)


@pytest.mark.asyncio
async def test_round_trip_iupac_missing():
    v = RoundTripValidator(
        iupac_provider=_FakeIUPAC({}),
        opsin_provider=_FakeOPSIN({}),
    )
    out = await v.normalize("CCO")
    assert out.iupac is None
    assert not out.round_trip_ok
    assert 0 < out.round_trip_score < 1.0  # partial credit for valid structure


@pytest.mark.asyncio
async def test_unparseable_input():
    v = RoundTripValidator(
        iupac_provider=_FakeIUPAC({}),
        opsin_provider=_FakeOPSIN({}),
    )
    out = await v.normalize("xxxxx")
    assert out.canonical_smiles == ""
    assert out.round_trip_score == 0.0
