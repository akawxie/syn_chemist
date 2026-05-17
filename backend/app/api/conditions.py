"""POST /api/conditions — Module B endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..modules.conditions import run_conditions

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


class ConditionsRequest(BaseModel):
    reactant: str
    product: str
    reagent: str | None = None
    reaction_class_hint: str | None = None


@router.post("")
async def conditions(req: ConditionsRequest) -> dict:
    return await run_conditions(
        req.reactant,
        req.product,
        reagent=req.reagent,
        reaction_class_hint=req.reaction_class_hint,
    )
