"""Google Gemini judge."""
from __future__ import annotations

from ..cache import cached
from ..config import settings
from .base import JudgeProvider, JudgeResult


class GeminiJudge(JudgeProvider):
    name = "gemini"

    def __init__(self) -> None:
        self._configured = False
        self._model = None
        if settings.google_api_key:
            try:
                import google.generativeai as genai  # type: ignore[import-not-found]
                genai.configure(api_key=settings.google_api_key)
                self._model = genai.GenerativeModel(settings.gemini_model)
                self._configured = True
            except Exception:
                self._configured = False

    @cached("judge:gemini")
    async def judge(self, system: str, user: str) -> JudgeResult:
        if not self._configured or self._model is None:
            raise RuntimeError("GOOGLE_API_KEY is not set or google-generativeai not installed.")
        prompt = f"{system}\n\n---\n\n{user}"
        resp = await self._model.generate_content_async(
            prompt,
            generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
        )
        text = getattr(resp, "text", "") or ""
        parsed = self.extract_json(text)
        return JudgeResult(
            raw_text=text,
            parsed=parsed,
            self_confidence=self.confidence_from(parsed),
            provider=self.name,
            model=settings.gemini_model,
        )
