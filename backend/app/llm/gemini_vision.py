"""Gemini Vision OCR for chemical structure images.

LLM = judgement, not source of truth: this module returns a raw SMILES guess,
which the molecule-image API endpoint then funnels through the existing
PubChem/OPSIN round-trip validator. OCR failures fall through as warnings,
never as silent successes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rdkit import Chem
from rdkit import RDLogger

from ..config import settings

_OCR_PROMPT = """You are a chemical-structure OCR engine.
Look at the image and return ONLY the canonical SMILES for the depicted molecule.

Rules:
- Return ONLY a SMILES string. No markdown fences, no explanation, no quotes, no prose.
- If multiple disconnected molecules appear, join with "."
- If the image clearly is NOT a chemical structure (photo, text-only, blank), return exactly: NOT_A_MOLECULE
- If you can see a structure but cannot determine atoms/bonds confidently, return exactly: UNCERTAIN
""".strip()


class NotAMoleculeError(Exception):
    """Raised when the OCR confidently says the image is not a chemical structure."""


@dataclass
class OCRResult:
    smiles: str  # empty if not extractable
    raw: str
    warning: str | None = None  # populated when SMILES not extractable but image was a structure


class VisionOCR(Protocol):
    async def smiles_from_image(self, image_bytes: bytes, mime: str) -> OCRResult: ...


def _clean_smiles_candidate(raw: str) -> str:
    """Strip code fences, quotes, leading/trailing whitespace."""
    s = (raw or "").strip()
    # Strip ```smiles ... ``` or ``` ... ```
    if s.startswith("```"):
        # remove first line up to newline
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        else:
            s = s.lstrip("`")
        if s.endswith("```"):
            s = s[:-3]
    s = s.strip().strip('"').strip("'").strip()
    # Some models wrap with `<smiles>` etc.
    if s.lower().startswith("smiles:"):
        s = s[7:].strip()
    return s


def _is_valid_smiles(s: str) -> bool:
    if not s:
        return False
    # SMILES contains no whitespace; reject prose before RDKit (which is
    # surprisingly permissive about spaces in some builds).
    if any(c.isspace() for c in s):
        return False
    RDLogger.DisableLog("rdApp.error")
    try:
        return Chem.MolFromSmiles(s) is not None
    finally:
        RDLogger.EnableLog("rdApp.error")


class GeminiVisionOCR:
    """Gemini Flash Lite vision OCR. Caller is responsible for image validation."""

    name = "gemini-vision"

    def __init__(self) -> None:
        self._configured = False
        self._client = None
        self._model_name: str = ""
        if settings.google_api_key:
            try:
                from google import genai  # type: ignore[import-not-found]

                self._client = genai.Client(api_key=settings.google_api_key)
                self._model_name = settings.gemini_vision_model
                self._configured = True
            except Exception:
                self._configured = False

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def smiles_from_image(self, image_bytes: bytes, mime: str) -> OCRResult:
        if not self._configured or self._client is None:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set or google-genai not installed."
            )
        from google.genai import types  # type: ignore[import-not-found]
        from ._retry import with_retry

        async def _call():
            return await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    _OCR_PROMPT,
                ],
                config=types.GenerateContentConfig(temperature=0.0),
            )

        resp, _retries = await with_retry(_call)
        raw = (getattr(resp, "text", "") or "").strip()
        return parse_ocr_response(raw)


def parse_ocr_response(raw: str) -> OCRResult:
    """Pure-function parser — separated so tests can drive it without Gemini."""
    cleaned = _clean_smiles_candidate(raw)
    if not cleaned:
        return OCRResult(smiles="", raw=raw, warning="OCR returned empty response")
    upper = cleaned.upper()
    if upper == "NOT_A_MOLECULE":
        raise NotAMoleculeError("OCR classified image as non-molecule")
    if upper == "UNCERTAIN":
        return OCRResult(smiles="", raw=raw, warning="OCR uncertain about structure")
    if _is_valid_smiles(cleaned):
        return OCRResult(smiles=cleaned, raw=raw)
    return OCRResult(
        smiles="",
        raw=raw,
        warning=f"OCR returned invalid SMILES: {cleaned[:80]}",
    )
