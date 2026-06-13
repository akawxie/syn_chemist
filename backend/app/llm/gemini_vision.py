"""Gemini Vision: OCR (SMILES extraction) and direct vision judge (image → module analysis).

Two distinct roles:
- GeminiVisionOCR: image → SMILES (feeds the existing SMILES pipeline).
- GeminiVisionJudge: image → structured module analysis (FGA / retro / conditions),
  bypassing the SMILES intermediate entirely.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, Protocol

from rdkit import Chem, RDLogger

from ..config import settings
from ..i18n import Lang, lang_name

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
        s = s[nl + 1 :] if nl != -1 else s.lstrip("`")
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


# ---------------------------------------------------------------------------
# GeminiVisionJudge — direct image → module analysis (no SMILES intermediate)
# ---------------------------------------------------------------------------

ModuleKind = Literal["fga", "retro", "conditions"]


def _extract_json(raw: str) -> dict:
    """Strip optional markdown fences and parse JSON."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        s = s.rsplit("```", 1)[0]
    try:
        return json.loads(s.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned non-JSON: {s[:200]}") from exc


class GeminiVisionJudge:
    """Direct image → structured chemistry analysis using Gemini multimodal.

    Renders the appropriate vision_<module>.j2 prompt template and calls
    settings.gemini_model (full Flash, not Lite) for better reasoning quality.
    """

    name = "gemini-vision-judge"

    def __init__(self) -> None:
        self._configured = False
        self._client = None
        self._model_name: str = ""
        if settings.google_api_key:
            try:
                from google import genai  # type: ignore[import-not-found]

                self._client = genai.Client(api_key=settings.google_api_key)
                self._model_name = settings.gemini_model  # full Flash, not Lite
                self._configured = True
            except Exception:
                self._configured = False

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def _call(self, image_bytes: bytes, mime: str, prompt: str) -> dict:
        if not self._configured or self._client is None:
            raise RuntimeError("GOOGLE_API_KEY is not set or google-genai not installed.")
        from google.genai import types  # type: ignore[import-not-found]

        from ._retry import with_retry

        async def _req():
            return await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                    prompt,
                ],
                config=types.GenerateContentConfig(temperature=0.0),
            )

        resp, _retries = await with_retry(_req)
        raw = (getattr(resp, "text", "") or "").strip()
        return _extract_json(raw)

    def _render(self, template: str, lang: Lang) -> str:
        from ..pipeline import prompts
        return prompts.render(template, output_language_name=lang_name(lang))

    async def analyze_for_fga(
        self, image_bytes: bytes, mime: str, lang: Lang = "en"
    ) -> dict:
        prompt = self._render("vision_fga.j2", lang)
        result = await self._call(image_bytes, mime, prompt)
        return {
            "module": "fga_vision",
            "structure_description": result.get("structure_description", ""),
            "alerts": result.get("alerts", []),
            "overall_self_confidence": result.get("overall_self_confidence", 0.0),
            "judge": {"provider": "gemini", "model": self._model_name},
        }

    async def analyze_for_retro(
        self, image_bytes: bytes, mime: str, lang: Lang = "en"
    ) -> dict:
        prompt = self._render("vision_retro.j2", lang)
        result = await self._call(image_bytes, mime, prompt)
        return {
            "module": "retro_vision",
            "structure_description": result.get("structure_description", ""),
            "routes": result.get("routes", []),
            "overall_self_confidence": result.get("overall_self_confidence", 0.0),
            "judge": {"provider": "gemini", "model": self._model_name},
        }

    async def analyze_for_conditions(
        self, image_bytes: bytes, mime: str, lang: Lang = "en"
    ) -> dict:
        prompt = self._render("vision_conditions.j2", lang)
        result = await self._call(image_bytes, mime, prompt)
        return {
            "module": "conditions_vision",
            "reaction_description": result.get("reaction_description", ""),
            "reaction_class_guess": result.get("reaction_class_guess", ""),
            "candidates": result.get("candidates", []),
            "overall_self_confidence": result.get("overall_self_confidence", 0.0),
            "judge": {"provider": "gemini", "model": self._model_name},
        }
