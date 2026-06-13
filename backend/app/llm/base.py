"""JudgeProvider ABC + factory.

Every provider returns the same shape so modules don't care which model is in play.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..config import settings


@dataclass
class JudgeResult:
    raw_text: str
    parsed: dict[str, Any]
    self_confidence: float  # extracted from parsed['overall_self_confidence'] or default
    provider: str
    model: str
    retry_count: int = 0
    json_retry: bool = False


class JudgeProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def judge(self, system: str, user: str) -> JudgeResult:
        """Return a JudgeResult. Implementations must enforce JSON output."""

    # ---------- Helpers shared by all providers ----------

    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        """Tolerant JSON extractor: handles ```json fences and stray prose."""
        if not text:
            return {}
        # Strip code fences.
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        # Try direct parse first.
        try:
            return json.loads(text)
        except Exception:
            pass
        # Find first '{' ... last '}'.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
        return {}

    @staticmethod
    def confidence_from(parsed: dict[str, Any], default: float = 0.5) -> float:
        v = parsed.get("overall_self_confidence")
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return default


_JSON_REPROMPT_SUFFIX = (
    "\n\nYour previous response was not valid JSON. "
    "Return ONLY the JSON object — no markdown fences, no prose."
)


async def try_parse_or_reprompt(
    provider: JudgeProvider, system: str, user: str
) -> JudgeResult:
    """Call provider.judge; if parsed is empty but raw_text non-empty, retry once.

    The reprompt appends a strict-JSON directive to the system prompt.
    """
    result = await provider.judge(system, user)
    if result.parsed or not (result.raw_text or "").strip():
        return result
    # Re-prompt once with a stricter system message.
    stricter_system = system + _JSON_REPROMPT_SUFFIX
    second = await provider.judge(stricter_system, user)
    second.json_retry = True
    second.retry_count = result.retry_count + second.retry_count
    if not second.parsed:
        # Keep latest raw_text so UI can surface it via NarrativeBlock.
        return second
    return second


def get_judge_provider() -> JudgeProvider:
    """Factory honoring settings.judge_provider."""
    provider = settings.judge_provider
    if provider == "deepseek":
        from .deepseek import DeepSeekJudge
        return DeepSeekJudge()
    if provider == "openai":
        from .openai_provider import OpenAIJudge
        return OpenAIJudge()
    if provider == "anthropic":
        from .anthropic_provider import AnthropicJudge
        return AnthropicJudge()
    if provider == "gemini":
        from .gemini_provider import GeminiJudge
        return GeminiJudge()
    raise ValueError(f"Unknown judge_provider: {provider}")
