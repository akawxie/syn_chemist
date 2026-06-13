"""DeepSeek V4 judge — primary provider.

DeepSeek's API is OpenAI-compatible, so we use the openai SDK pointed at
https://api.deepseek.com/v1. Default model: 'deepseek-chat'.
"""
from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from ..cache import cached
from ..config import settings
from ._retry import with_retry
from .base import JudgeProvider, JudgeResult

# LLM calls for complex molecules can take 60–90s; cap at 120s so the UI
# gets a timely error instead of hanging for the SDK's default 600s.
_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=10.0)


class DeepSeekJudge(JudgeProvider):
    name = "deepseek"

    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            # Defer error to call time so import + tests work without a key.
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                timeout=_TIMEOUT,
                max_retries=0,  # we use with_retry for consistent retry logic
            )

    @cached("judge:deepseek")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if self._client is None:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Add it to backend/.env or switch judge_provider."
            )

        async def _call():
            return await self._client.chat.completions.create(
                model=settings.deepseek_model,
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
            model=settings.deepseek_model,
            retry_count=retries,
        )
