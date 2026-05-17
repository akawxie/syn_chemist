"""DeepSeek V4 judge — primary provider.

DeepSeek's API is OpenAI-compatible, so we use the openai SDK pointed at
https://api.deepseek.com/v1. Default model: 'deepseek-chat'.
"""
from __future__ import annotations

from openai import AsyncOpenAI

from ..cache import cached
from ..config import settings
from .base import JudgeProvider, JudgeResult


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
            )

    @cached("judge:deepseek")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if self._client is None:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Add it to backend/.env or switch judge_provider."
            )
        resp = await self._client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content or ""
        parsed = self.extract_json(text)
        return JudgeResult(
            raw_text=text,
            parsed=parsed,
            self_confidence=self.confidence_from(parsed),
            provider=self.name,
            model=settings.deepseek_model,
        )
