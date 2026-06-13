"""Settings — read from env / .env. Centralized so providers and weights are tweakable."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Storage ---
    sqlite_path: Path = Path("./data/ai_chemist.db")

    # --- LLM provider selection (judge layer) ---
    # DeepSeek is the primary per product decision. The provider is OpenAI-compatible.
    judge_provider: Literal["deepseek", "openai", "anthropic", "gemini"] = "deepseek"

    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"  # latest non-reasoning model alias

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-4-7"

    google_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_vision_model: str = "gemini-2.5-flash-lite"  # P2 image OCR; override via env

    # --- Naming providers ---
    # 'stout_local' requires the optional 'stout' extra. 'opsin_web' uses the public CAM service.
    iupac_provider: Literal["stout_local", "pubchem", "pubchem_stout", "opsin_web", "stub"] = "stub"
    opsin_provider: Literal["py2opsin", "opsin_web"] = "py2opsin"
    opsin_web_url: str = "https://opsin.ch.cam.ac.uk/opsin"

    # --- Confidence weighting (must sum ~1.0) ---
    confidence_weight_round_trip: float = 0.3
    confidence_weight_judge: float = 0.3
    confidence_weight_verify: float = 0.4

    # --- HTTP / CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Cache ---
    cache_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days


settings = Settings()
settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
