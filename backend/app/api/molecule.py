"""POST /api/molecule/normalize — SMILES↔IUPAC round-trip without LLM involvement."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..pipeline.naming import RoundTripValidator

router = APIRouter(prefix="/api/molecule", tags=["molecule"])


class NormalizeRequest(BaseModel):
    input: str


@router.post("/normalize")
async def normalize(req: NormalizeRequest) -> dict:
    validator = RoundTripValidator()
    n = await validator.normalize(req.input)
    return n.__dict__
