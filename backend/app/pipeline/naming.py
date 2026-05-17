"""Naming providers: SMILES↔IUPAC with closed-loop validation.

The PRD's central correctness mechanism. STOUT (or successor) goes SMILES→IUPAC;
OPSIN goes IUPAC→SMILES; we then compare canonical SMILES on both ends.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
from rdkit import Chem

from ..cache import cached
from ..config import settings

# ---------- Data ----------


@dataclass
class NormalizedMolecule:
    input_raw: str
    canonical_smiles: str
    iupac: str | None
    round_trip_ok: bool
    round_trip_score: float  # 0..1; 1.0 = canonical SMILES match
    notes: list[str]


# ---------- Provider interfaces (PRD §4 pluggability) ----------


class IUPACProvider(Protocol):
    async def to_iupac(self, smiles: str) -> str | None: ...


class OPSINProvider(Protocol):
    async def to_smiles(self, iupac: str) -> str | None: ...


# ---------- Helpers ----------


def _looks_like_mol_block(text: str) -> bool:
    """Detect CTfile / MDL MOL block by structural markers, regardless of header line."""
    if "\n" not in text:
        return False
    return "V2000" in text or "V3000" in text or "M  END" in text


def to_canonical_smiles(text: str) -> str | None:
    """Accept SMILES, InChI, or MOL block; return canonical SMILES or None on parse failure."""
    if not text:
        return None
    mol = None
    if _looks_like_mol_block(text):
        # MOL block: keep original whitespace — RDKit needs the 3 fixed header lines
        mol = Chem.MolFromMolBlock(text)
        if mol is None:
            return None
        try:
            return Chem.MolToSmiles(mol, canonical=True)
        except Exception:
            return None
    text = text.strip()
    if text.lower().startswith("inchi="):
        mol = Chem.MolFromInchi(text)
    if mol is None:
        # Last resort: try as SMILES. RDKit will log a parse error if it fails;
        # we silence the global RDKit logger to keep server logs clean on bad input.
        from rdkit import RDLogger
        RDLogger.DisableLog("rdApp.error")
        try:
            mol = Chem.MolFromSmiles(text)
        finally:
            RDLogger.EnableLog("rdApp.error")
    if mol is None:
        return None
    try:
        return Chem.MolToSmiles(mol, canonical=True)
    except Exception:
        return None


def smiles_equiv(a: str | None, b: str | None) -> bool:
    """Canonical-SMILES equality (not raw-string)."""
    if not a or not b:
        return False
    ca = to_canonical_smiles(a)
    cb = to_canonical_smiles(b)
    return ca is not None and ca == cb


# ---------- IUPAC providers ----------


class StubIUPACProvider:
    """Default fallback that returns None — naming round-trip will be skipped."""

    async def to_iupac(self, smiles: str) -> str | None:  # noqa: D401
        return None


class PubChemIUPACProvider:
    """PubChem REST: SMILES → IUPAC name. Free, no key, works for compounds PubChem indexes."""

    @cached("pubchem:iupac")
    async def to_iupac(self, smiles: str) -> str | None:
        try:
            from urllib.parse import quote
            url = (
                f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/"
                f"{quote(smiles, safe='')}/property/IUPACName/TXT"
            )
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return None
                name = r.text.strip().splitlines()[0].strip() if r.text else ""
                return name or None
        except Exception:
            return None


class ChainedIUPACProvider:
    """Try providers in order; first non-empty IUPAC wins."""

    def __init__(self, providers: list[IUPACProvider]) -> None:
        self._providers = providers

    async def to_iupac(self, smiles: str) -> str | None:
        for p in self._providers:
            try:
                name = await p.to_iupac(smiles)
            except Exception:
                name = None
            if name:
                return name
        return None


class StoutIUPACProvider:
    """STOUT (Smiles-TO-iUpac-Translator). Optional dep, only loaded on demand."""

    def __init__(self) -> None:
        self._translator = None

    def _load(self):
        if self._translator is None:
            from STOUT import translate_forward  # type: ignore[import-not-found]
            self._translator = translate_forward
        return self._translator

    @cached("stout")
    async def to_iupac(self, smiles: str) -> str | None:
        try:
            t = self._load()
            return t(smiles)
        except Exception:
            return None


# ---------- OPSIN providers ----------


class Py2OpsinProvider:
    """Local OPSIN jar via py2opsin. Synchronous under the hood; cached."""

    @cached("opsin:py2opsin")
    async def to_smiles(self, iupac: str) -> str | None:
        try:
            from py2opsin import py2opsin  # type: ignore[import-not-found]
            result = py2opsin(iupac, output_format="SMILES")
            if isinstance(result, list):
                result = result[0] if result else ""
            return result or None
        except Exception:
            return None


class OpsinWebProvider:
    """Public OPSIN web service at opsin.ch.cam.ac.uk."""

    @cached("opsin:web")
    async def to_smiles(self, iupac: str) -> str | None:
        url = f"{settings.opsin_web_url}/{iupac}.smi"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return None
                return r.text.strip() or None
        except Exception:
            return None


# ---------- Selection ----------


def get_iupac_provider() -> IUPACProvider:
    mode = settings.iupac_provider
    if mode == "stout_local":
        return StoutIUPACProvider()
    if mode == "pubchem":
        return PubChemIUPACProvider()
    if mode == "pubchem_stout":
        return ChainedIUPACProvider([PubChemIUPACProvider(), StoutIUPACProvider()])
    return StubIUPACProvider()


def get_opsin_provider() -> OPSINProvider:
    if settings.opsin_provider == "opsin_web":
        return OpsinWebProvider()
    return Py2OpsinProvider()


# ---------- Round-trip validator ----------


class RoundTripValidator:
    def __init__(
        self,
        iupac_provider: IUPACProvider | None = None,
        opsin_provider: OPSINProvider | None = None,
    ) -> None:
        self.iupac = iupac_provider or get_iupac_provider()
        self.opsin = opsin_provider or get_opsin_provider()

    async def normalize(self, raw_input: str) -> NormalizedMolecule:
        notes: list[str] = []
        canonical = to_canonical_smiles(raw_input)
        if canonical is None:
            return NormalizedMolecule(
                input_raw=raw_input,
                canonical_smiles="",
                iupac=None,
                round_trip_ok=False,
                round_trip_score=0.0,
                notes=["Could not parse input as SMILES or InChI."],
            )

        iupac = await self.iupac.to_iupac(canonical)
        if iupac is None:
            notes.append("IUPAC provider returned no name; round-trip skipped.")
            return NormalizedMolecule(
                input_raw=raw_input,
                canonical_smiles=canonical,
                iupac=None,
                round_trip_ok=False,
                round_trip_score=0.5,  # partial: structure is valid even if naming unavailable
                notes=notes,
            )

        back = await self.opsin.to_smiles(iupac)
        if back is None:
            notes.append(f"OPSIN could not parse IUPAC '{iupac}'.")
            return NormalizedMolecule(
                input_raw=raw_input,
                canonical_smiles=canonical,
                iupac=iupac,
                round_trip_ok=False,
                round_trip_score=0.4,
                notes=notes,
            )

        ok = smiles_equiv(canonical, back)
        return NormalizedMolecule(
            input_raw=raw_input,
            canonical_smiles=canonical,
            iupac=iupac,
            round_trip_ok=ok,
            round_trip_score=1.0 if ok else 0.5,
            notes=notes
            if ok
            else notes + [f"Round-trip mismatch: {canonical} != {to_canonical_smiles(back)}"],
        )
