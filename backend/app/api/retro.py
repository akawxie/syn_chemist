"""POST /api/retro — Module C endpoint (SMILES path + vision path)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..llm.gemini_vision import GeminiVisionJudge
from ..modules.retro import run_retro
from ._image_utils import validate_image

router = APIRouter(prefix="/api/retro", tags=["retro"])


class RetroRequest(BaseModel):
    target: str
    lang: Literal["en", "zh"] = "en"


@router.post("")
async def retro(req: RetroRequest) -> dict:
    return await run_retro(req.target, lang=req.lang)


@router.post("/from_image")
async def retro_from_image(
    file: UploadFile = File(...),
    lang: Literal["en", "zh"] = "en",
) -> dict:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="empty upload")
    validated_bytes, mime = validate_image(raw)
    judge = GeminiVisionJudge()
    if not judge.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Vision analysis unavailable — GOOGLE_API_KEY is not configured.",
        )
    return await judge.analyze_for_retro(validated_bytes, mime, lang=lang)
