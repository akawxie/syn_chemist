"""POST /api/conditions — Module B endpoint (SMILES path + vision path)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..llm.gemini_vision import GeminiVisionJudge
from ..modules.conditions import run_conditions
from ._image_utils import validate_image

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


class ConditionsRequest(BaseModel):
    reactant: str
    product: str
    reagent: str | None = None
    reaction_class_hint: str | None = None
    lang: Literal["en", "zh"] = "en"


@router.post("")
async def conditions(req: ConditionsRequest) -> dict:
    return await run_conditions(
        req.reactant,
        req.product,
        reagent=req.reagent,
        reaction_class_hint=req.reaction_class_hint,
        lang=req.lang,
    )


@router.post("/from_image")
async def conditions_from_image(
    file: UploadFile = File(...),
    lang: Literal["en", "zh"] = Form("en"),
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
    return await judge.analyze_for_conditions(validated_bytes, mime, lang=lang)
