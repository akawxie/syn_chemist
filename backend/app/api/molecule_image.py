"""POST /api/molecule/from_image — Gemini vision OCR + round-trip validation.

Returns a NormalizedMolecule shape extended with `ocr_raw` and `warning` fields
so the UI can show both the detected SMILES *and* a banner when round-trip
validation failed.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException, UploadFile, File
from PIL import Image, UnidentifiedImageError

from ..llm.gemini_vision import (
    GeminiVisionOCR,
    NotAMoleculeError,
    OCRResult,
    VisionOCR,
)
from ..pipeline.naming import RoundTripValidator

router = APIRouter(prefix="/api/molecule", tags=["molecule"])

# Accepted MIME types and corresponding PIL formats
_ALLOWED_PIL_FORMATS = {"PNG", "JPEG", "WEBP"}
_PIL_FORMAT_TO_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_MIN_DIM = 200
_MAX_DIM = 4096


def _validate_image(raw: bytes) -> tuple[bytes, str]:
    """Validate by content (PIL), not header. Returns (raw_or_downscaled, mime)."""
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 5 MB)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()  # detect corrupt files
    except (UnidentifiedImageError, Exception) as e:  # noqa: BLE001
        raise HTTPException(status_code=415, detail=f"not a recognized image: {e}") from e
    # PIL.verify() requires a fresh open for further ops
    img = Image.open(io.BytesIO(raw))
    fmt = (img.format or "").upper()
    if fmt not in _ALLOWED_PIL_FORMATS:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported image format: {fmt or 'unknown'} (allowed: PNG/JPEG/WEBP)",
        )
    w, h = img.size
    short = min(w, h)
    long_side = max(w, h)
    if short < _MIN_DIM:
        raise HTTPException(
            status_code=400,
            detail=f"image too small (min {_MIN_DIM}px on shortest side, got {short}px)",
        )
    if long_side > _MAX_DIM:
        # Downscale to <=2048 on long side
        scale = 2048 / long_side
        img = img.convert("RGB" if fmt == "JPEG" else "RGBA" if fmt == "PNG" else "RGB")
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        raw = buf.getvalue()
    return raw, _PIL_FORMAT_TO_MIME[fmt]


async def _run_ocr_and_normalize(
    raw: bytes, mime: str, ocr: VisionOCR, validator: RoundTripValidator
) -> dict:
    try:
        ocr_result: OCRResult = await ocr.smiles_from_image(raw, mime)
    except NotAMoleculeError:
        raise HTTPException(
            status_code=422,
            detail="image does not appear to depict a chemical structure",
        ) from None

    payload: dict = {
        "ocr_raw": ocr_result.raw,
        "warning": ocr_result.warning,
        "smiles": ocr_result.smiles,
    }
    if not ocr_result.smiles:
        # Could not extract a usable SMILES — return a 200 with warning so UI shows the message.
        payload.update(
            {
                "canonical_smiles": "",
                "iupac": None,
                "round_trip_ok": False,
                "round_trip_score": 0.0,
                "notes": ["OCR did not return a usable SMILES"],
            }
        )
        return payload

    normalized = await validator.normalize(ocr_result.smiles)
    payload.update(
        {
            "input_raw": ocr_result.smiles,
            "canonical_smiles": normalized.canonical_smiles,
            "iupac": normalized.iupac,
            "round_trip_ok": normalized.round_trip_ok,
            "round_trip_score": normalized.round_trip_score,
            "notes": normalized.notes,
        }
    )
    if not normalized.round_trip_ok and not payload.get("warning"):
        payload["warning"] = "OCR result not verified by round-trip"
    return payload


@router.post("/from_image")
async def from_image(file: UploadFile = File(...)) -> dict:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="empty upload")
    validated_bytes, mime = _validate_image(raw)
    ocr = GeminiVisionOCR()
    validator = RoundTripValidator()
    return await _run_ocr_and_normalize(validated_bytes, mime, ocr, validator)
