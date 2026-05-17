"""FastAPI app entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import conditions as conditions_api
from .api import fga as fga_api
from .api import molecule as molecule_api
from .api import retro as retro_api
from .config import settings
from .db import get_engine

app = FastAPI(
    title="AI_chemist",
    version="0.1.0",
    description="Generate–judge–verify pipeline for synthetic chemistry. "
    "DeepSeek V4 as primary judge; RDKit/STOUT/OPSIN as verifiers.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    get_engine()  # creates SQLite tables.


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "judge_provider": settings.judge_provider,
        "iupac_provider": settings.iupac_provider,
        "opsin_provider": settings.opsin_provider,
    }


app.include_router(molecule_api.router)
app.include_router(fga_api.router)
app.include_router(conditions_api.router)
app.include_router(retro_api.router)
