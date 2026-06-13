"""OpenAI judge (GPT)."""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from ..cache import cached
from ..config import settings
from ._retry import with_retry
from .base import JudgeProvider, JudgeResult

_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=10.0)


class OpenAIJudge(JudgeProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key, timeout=_TIMEOUT, max_retries=0)
            if settings.openai_api_key else None
        )

    @cached("judge:openai")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        async def _call():
            return await self._client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

        resp, retries = await with_retry(_call)
        text = resp.choices[0].message.content or ""
        parsed = self.extract_json(text)
        return JudgeResult(
            raw_text=text,
            parsed=parsed,
            self_confidence=self.confidence_from(parsed),
            provider=self.name,
            model=settings.openai_model,
            retry_count=retries,
        )
