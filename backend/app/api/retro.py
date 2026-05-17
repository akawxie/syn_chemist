"""POST /api/retro — Module C endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..modules.retro import run_retro

router = APIRouter(prefix="/api/retro", tags=["retro"])


class RetroRequest(BaseModel):
    target: str


@router.post("")
async def retro(req: RetroRequest) -> dict:
    return await run_retro(req.target)
