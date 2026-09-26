"""
coach_llm.py - chat client for the AI coach (post-match and career reviews).

Separate from llm_provider.py (live advice): no hard 6 s limit, bigger answers,
runs on the service's AI job thread only. Speaks the OpenAI-compatible chat
API of Groq and OpenRouter, whose free tiers serve openai/gpt-oss-120b.

The key comes from the app settings (entered by the player, stored locally)
or, for development, from GROQ_API_KEY / OPENROUTER_API_KEY in the env.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from app.config import GROQ_API_KEY, GROQ_MODEL, LLM_PROVIDER, OPENROUTER_API_KEY, OPENROUTER_MODEL

PROVIDERS: dict[str, dict[str, str]] = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": GROQ_MODEL or "openai/gpt-oss-120b",
        "label": "Groq",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": OPENROUTER_MODEL or "openai/gpt-oss-120b:free",
        "label": "OpenRouter",
    },
}
DEFAULT_TIMEOUT = 120.0
CHECK_TIMEOUT = 30.0


class CoachLLMError(Exception):
    """code: no_key | invalid_key | rate_limited | timeout | offline | bad_response."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass
class AISettings:
    provider: str
    api_key: str
    model: str
    source: str  # "app" (entered in the launcher) or "env"

    def public(self) -> dict[str, Any]:
        """Never includes the key itself."""
        return {
            "configured": bool(self.api_key),
            "provider": self.provider,
            "provider_label": PROVIDERS[self.provider]["label"],
            "model": self.model,
            "source": self.source,
            "key_hint": f"…{self.api_key[-4:]}" if len(self.api_key) >= 8 else "",
        }


def settings_from(data: dict[str, Any] | None, *, source: str) -> AISettings | None:
    if not data:
        return None
    provider = str(data.get("provider") or "").strip().lower()
    key = str(data.get("api_key") or "").strip()
    if provider not in PROVIDERS or not key:
        return None
    model = str(data.get("model") or "").strip() or PROVIDERS[provider]["model"]
    return AISettings(provider=provider, api_key=key, model=model, source=source)


def env_settings() -> AISettings | None:
    """Developer keys from .env: the live LLM provider if it has a key, else any key."""
    keys = {"groq": GROQ_API_KEY, "openrouter": OPENROUTER_API_KEY}
    order = [LLM_PROVIDER] if LLM_PROVIDER in keys else []
    for provider in [*order, "groq", "openrouter"]:
        if keys.get(provider):
            return settings_from({"provider": provider, "api_key": keys[provider]}, source="env")
    return None


class CoachLLM:
    def __init__(
        self,
        settings: AISettings,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        session: Any = None,
    ) -> None:
        self.settings = settings
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def label(self) -> dict[str, str]:
        return {"provider": self.settings.provider, "model": self.settings.model}

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int = 6000) -> str:
        """The assistant message text; raises CoachLLMError."""
        settings = self.settings
        if not settings.api_key:
            raise CoachLLMError("no_key")
        payload: dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if "gpt-oss" in settings.model:
            # Reasoning models: think before writing; the answer stays in "content".
            if settings.provider == "groq":
                payload["reasoning_effort"] = "medium"
            else:
                payload["reasoning"] = {"effort": "medium", "exclude": True}
        headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        if settings.provider == "openrouter":
            headers["X-Title"] = "Dota AI Coach"
        response = self._post(headers, payload)
        if getattr(response, "status_code", 0) == 400:
            # Some models or routes reject JSON mode or the reasoning option:
            # ask once more without them (the prompt already demands JSON).
            for key in ("response_format", "reasoning_effort", "reasoning"):
                payload.pop(key, None)
            response = self._post(headers, payload)
        status = getattr(response, "status_code", 0)
        if status in (401, 403):
            raise CoachLLMError("invalid_key")
        if status == 429:
            raise CoachLLMError("rate_limited")
        if status >= 400:
            raise CoachLLMError("bad_response", f"HTTP {status}")
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise CoachLLMError("bad_response", "unexpected response shape") from error
        if not isinstance(content, str) or not content.strip():
            raise CoachLLMError("bad_response", "empty answer")
        return content.strip()

    def _post(self, headers: dict[str, str], payload: dict[str, Any]) -> Any:
        try:
            return self.session.post(
                PROVIDERS[self.settings.provider]["url"],
                headers=headers,
                json=payload,
                timeout=(10, self.timeout),
            )
        except requests.Timeout as error:
            raise CoachLLMError("timeout") from error
        except requests.RequestException as error:
            raise CoachLLMError("offline", _redact(str(error), self.settings.api_key)) from error

    def check(self) -> None:
        """A tiny request to validate the key and model."""
        content = self.complete(
            [
                {"role": "system", "content": "Answer with JSON only."},
                {"role": "user", "content": 'Reply with {"ok": true}.'},
            ],
            max_tokens=400,
        )
        parse_json_object(content)


def parse_json_object(content: str) -> dict[str, Any]:
    """The first JSON object in the answer (models sometimes wrap it in text or fences)."""
    text = content.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise CoachLLMError("bad_response", "no JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise CoachLLMError("bad_response", "invalid JSON") from error
    if not isinstance(data, dict):
        raise CoachLLMError("bad_response", "JSON is not an object")
    return data


def _redact(message: str, key: str) -> str:
    return (message.replace(key, "[key]") if key else message)[:300]
