"""
coach_llm.py - chat client for the AI coach (post-match and career reviews).

Separate from llm_provider.py (live advice): no hard 6 s limit, bigger answers,
runs on the service's AI job thread only. Speaks the OpenAI-compatible chat
API of Google Gemini (free AI Studio tier, Gemini Flash), Groq and OpenRouter
(free openai/gpt-oss-120b).

The key comes from the app settings (entered by the player, stored locally)
or, for development, from GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY
in the env.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)

# First entry = the default choice in the launcher.
PROVIDERS: dict[str, dict[str, str]] = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "model": GEMINI_MODEL or "gemini-3.8-flash",
        "label": "Gemini",
    },
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
# Free Gemini Flash models are often "experiencing high demand" (503) and each
# has its own free quota (429): on those, or a retired id (404), the next one
# is tried. Pro models have no free quota.
FALLBACK_MODELS: dict[str, list[str]] = {
    "gemini": ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"],
}
RETRY_NEXT_MODEL = {404, 429, 500, 503}
DEFAULT_TIMEOUT = 120.0
CHECK_TIMEOUT = 30.0


class CoachLLMError(Exception):
    """code: no_key | invalid_key | region | rate_limited | busy | timeout | offline |
    bad_response."""

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
    keys = {"gemini": GEMINI_API_KEY, "groq": GROQ_API_KEY, "openrouter": OPENROUTER_API_KEY}
    order = [LLM_PROVIDER] if LLM_PROVIDER in keys else []
    for provider in [*order, "gemini", "groq", "openrouter"]:
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
        fallbacks: bool = True,
    ) -> None:
        self.settings = settings
        self.timeout = timeout
        # False: only the chosen model (model comparisons).
        self.fallbacks = fallbacks
        self.session = session or requests.Session()
        self.used_model: str | None = None

    @property
    def label(self) -> dict[str, str]:
        return {"provider": self.settings.provider, "model": self.used_model or self.settings.model}

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
        # Reasoning models: think before writing; the answer stays in "content".
        if settings.provider == "gemini" or (
            settings.provider == "groq" and "gpt-oss" in settings.model
        ):
            payload["reasoning_effort"] = "medium"
        elif "gpt-oss" in settings.model:
            payload["reasoning"] = {"effort": "medium", "exclude": True}
        headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        if settings.provider == "openrouter":
            headers["X-Title"] = "Dota AI Coach"
        response = self._post(headers, payload)
        fallbacks = [m for m in FALLBACK_MODELS.get(settings.provider, []) if m != settings.model]
        if not self.fallbacks:
            fallbacks = []
        while getattr(response, "status_code", 0) in RETRY_NEXT_MODEL and fallbacks:
            payload["model"] = fallbacks.pop(0)
            response = self._post(headers, payload)
        if _region_blocked(response):
            # Gemini from Russia: HTTP 400 "User location is not supported"; Groq and
            # others answer 403 for countries they do not serve. Not a key problem.
            raise CoachLLMError("region")
        if getattr(response, "status_code", 0) == 400 and "api key" in _body(response).lower():
            # Google answers a wrong key with HTTP 400.
            raise CoachLLMError("invalid_key")
        if getattr(response, "status_code", 0) == 400:
            # Some models or routes reject JSON mode or the reasoning option:
            # ask once more without them (the prompt already demands JSON).
            for key in ("response_format", "reasoning_effort", "reasoning"):
                payload.pop(key, None)
            response = self._post(headers, payload)
        status = getattr(response, "status_code", 0)
        self.used_model = payload["model"]
        if _region_blocked(response):
            raise CoachLLMError("region")
        if status in (401, 403):
            raise CoachLLMError("invalid_key")
        if status == 429:
            raise CoachLLMError("rate_limited")
        if status in (500, 502, 503, 504):
            raise CoachLLMError("busy")
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


def _body(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text[:2000]
    try:
        return json.dumps(response.json())[:2000]
    except (ValueError, TypeError, AttributeError):
        return ""


def _redact(message: str, key: str) -> str:
    return (message.replace(key, "[key]") if key else message)[:300]


REGION_MARKERS = (
    "location is not supported",
    "user location",
    "unsupported_country",
    "country, region, or territory",
    "not available in your country",
    "not available in your region",
    "unsupported region",
)


def _region_blocked(response: Any) -> bool:
    if getattr(response, "status_code", 0) not in (400, 403, 451):
        return False
    body = _body(response).lower()
    return any(marker in body for marker in REGION_MARKERS)
