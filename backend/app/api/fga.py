"""POST /api/fga — Module A endpoint."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..modules.fga import run_fga

router = APIRouter(prefix="/api/fga", tags=["fga"])


class FGARequest(BaseModel):
    input: str
    lang: Literal["en", "zh"] = "en"


@router.post("")
async def fga(req: FGARequest) -> dict:
    return await run_fga(req.input, lang=req.lang)
