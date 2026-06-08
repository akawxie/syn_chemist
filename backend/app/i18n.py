"""i18n helpers for prompt language."""
from __future__ import annotations

from typing import Literal

Lang = Literal["en", "zh"]

LANG_NAMES: dict[str, str] = {
    "en": "English",
    "zh": "Chinese (Simplified, 简体中文)",
}


def lang_name(lang: str | None) -> str | None:
    """Return the prompt-friendly language name, or None for default (English)."""
    if lang is None or lang == "en":
        return None  # don't add the directive when EN is the default
    return LANG_NAMES.get(lang)
