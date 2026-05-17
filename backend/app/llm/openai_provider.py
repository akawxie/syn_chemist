"""OpenAI judge (GPT)."""
from __future__ import annotations

from openai import AsyncOpenAI

from ..cache import cached
from ..config import settings
from .base import JudgeProvider, JudgeResult


class OpenAIJudge(JudgeProvider):
    name = "openai"

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @cached("judge:openai")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        resp = await self._client.chat.completions.create(
            model=settings.openai_model,
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
            model=settings.openai_model,
        )
