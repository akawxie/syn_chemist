"""Shared image validation for all vision endpoints."""
from __future__ import annotations

import io

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

_ALLOWED_PIL_FORMATS = {"PNG", "JPEG", "WEBP"}
_PIL_FORMAT_TO_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_MAX_BYTES = 5 * 1024 * 1024
_MIN_DIM = 200
_MAX_DIM = 4096


def validate_image(raw: bytes) -> tuple[bytes, str]:
    """Validate image by content (not header). Returns (raw_or_downscaled, mime)."""
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 5 MB)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
    except (UnidentifiedImageError, Exception) as e:  # noqa: BLE001
        raise HTTPException(status_code=415, detail=f"not a recognized image: {e}") from e
    img = Image.open(io.BytesIO(raw))
    fmt = (img.format or "").upper()
    if fmt not in _ALLOWED_PIL_FORMATS:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported image format: {fmt or 'unknown'} (allowed: PNG/JPEG/WEBP)",
        )
    w, h = img.size
    if min(w, h) < _MIN_DIM:
        raise HTTPException(
            status_code=400,
            detail=f"image too small (min {_MIN_DIM}px on shortest side, got {min(w, h)}px)",
        )
    if max(w, h) > _MAX_DIM:
        scale = 2048 / max(w, h)
        img = img.convert("RGB" if fmt == "JPEG" else "RGBA" if fmt == "PNG" else "RGB")
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        raw = buf.getvalue()
    return raw, _PIL_FORMAT_TO_MIME[fmt]
