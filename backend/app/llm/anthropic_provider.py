"""Anthropic Claude judge — uses prompt caching for the system message."""
from __future__ import annotations

from anthropic import AsyncAnthropic

from ..cache import cached
from ..config import settings
from ._retry import with_retry
from .base import JudgeProvider, JudgeResult


class AnthropicJudge(JudgeProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self._client = (
            AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=120.0, max_retries=0)
            if settings.anthropic_api_key else None
        )

    @cached("judge:anthropic")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if self._client is None:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")

        async def _call():
            return await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user}],
                temperature=0.0,
            )

        resp, retries = await with_retry(_call)
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        parsed = self.extract_json(text)
        return JudgeResult(
            raw_text=text,
            parsed=parsed,
            self_confidence=self.confidence_from(parsed),
            provider=self.name,
            model=settings.anthropic_model,
            retry_count=retries,
        )
