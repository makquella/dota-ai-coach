"""Promo narration: selected Ukrainian Alex Nekrasov on ElevenLabs v4.

One continuous take is aligned and split for the scene renderer. Legacy models
can retain per-scene narration/context with explicit environment overrides.
ELEVENLABS_API_KEY is used only in request headers and never in metadata/logs.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=pcm_22050"
RATE = 22050
# Variant A selected by the developer after the live Telegram comparisons.
DEFAULT_VOICE = "9Sj8ugvpK1DmcAXyvi3a"
DEFAULT_VOICE_NAME = "Alex Nekrasov - Confident and Clear"
DEFAULT_MODEL = "eleven_v4"
SETTINGS = {"stability": 0.4, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}
TIMEOUT = 120
RETRIES = (2, 5, 15)
USER_AGENT = "Wardly promo"


def available() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())


def words_from_alignment(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    """Characters with start/end times -> [{"word", "start", "end"}] split on spaces."""
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    words: list[dict[str, Any]] = []
    current, start, end = "", 0.0, 0.0
    for char, s, e in zip(chars, starts, ends, strict=False):
        if char.isspace():
            if current:
                words.append({"word": current, "start": round(start, 3), "end": round(end, 3)})
            current = ""
            continue
        if not current:
            start = float(s)
        current += char
        end = float(e)
    if current:
        words.append({"word": current, "start": round(start, 3), "end": round(end, 3)})
    return words


def api_request(url: str, body: dict[str, Any] | None, key: str, *, method: str = "POST") -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for pause in (*RETRIES, None):
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "xi-api-key": key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            detail = error.read(500).decode("utf-8", "replace").replace(key, "[redacted]").strip()
            if error.code in (429, 500, 502, 503, 504) and pause is not None:
                time.sleep(pause)
                continue
            raise SystemExit(f"ElevenLabs: HTTP {error.code} {detail}") from None
        except (urllib.error.URLError, TimeoutError) as error:
            if pause is not None:
                time.sleep(pause)
                continue
            raise SystemExit("ElevenLabs: " + str(error).replace(key, "[redacted]")) from None
    raise SystemExit("ElevenLabs: no answer")


def _post(url: str, body: dict[str, Any], key: str) -> dict[str, Any]:
    return dict(api_request(url, body, key))


def settings(model: str) -> dict[str, Any]:
    values = dict(SETTINGS)
    if model in {"eleven_v3", "eleven_v4"}:
        values = {"stability": 0.5, "speed": 1.0}
    for name, env in (("stability", "ELEVENLABS_STABILITY"), ("speed", "ELEVENLABS_SPEED")):
        if os.environ.get(env):
            values[name] = float(os.environ[env])
    if not 0 <= values["stability"] <= 1 or not 0.7 <= values.get("speed", 1.0) <= 1.2:
        raise ValueError("Unsupported voice stability/speed")
    return values


def configuration() -> dict[str, Any]:
    """Effective non-secret settings, shared by narration and package metadata."""
    selected = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE
    model = os.environ.get("ELEVENLABS_MODEL", "").strip() or DEFAULT_MODEL
    modern = model in {"eleven_v3", "eleven_v4"}
    continuous = os.environ.get("ELEVENLABS_CONTINUOUS", "").strip().lower()
    if continuous not in {"", "true", "false"}:
        raise ValueError("ELEVENLABS_CONTINUOUS must be true or false")
    values = settings(model)
    return {
        "voice_id": selected,
        "name": os.environ.get("ELEVENLABS_VOICE_NAME", "").strip()
        or (DEFAULT_VOICE_NAME if selected == DEFAULT_VOICE else selected),
        "model": model,
        "language": os.environ.get("ELEVENLABS_LANGUAGE", "").strip() or ("uk" if modern else None),
        "stability": values["stability"],
        "speed": values.get("speed", 1.0),
        "continuous": continuous == "true" if continuous else modern,
    }


def synthesize(
    text: str, out: Path, previous: str = "", following: str = ""
) -> tuple[Path, list[dict[str, Any]]] | None:
    """(the WAV, its words with times), or None without an API key."""
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return None
    config = configuration()
    selected, model = config["voice_id"], config["model"]
    body: dict[str, Any] = {
        "text": text,
        "model_id": model,
        "voice_settings": settings(model),
    }
    if config["language"]:
        body["language_code"] = config["language"]
    if previous and model not in {"eleven_v3", "eleven_v4"}:
        body["previous_text"] = previous
    if following and model not in {"eleven_v3", "eleven_v4"}:
        body["next_text"] = following
    answer = _post(API.format(voice=selected), body, key)
    pcm = base64.b64decode(answer.get("audio_base64") or "")
    if not pcm:
        raise SystemExit("ElevenLabs: empty audio")
    with wave.open(str(out), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(pcm)
    return out, words_from_alignment(answer.get("alignment") or {})


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / float(audio.getframerate())


def join(parts: list[tuple[Path | None, float]], out: Path, rate: int = RATE) -> Path:
    """One WAV: each scene's voice (or silence) padded to the scene's length."""
    with wave.open(str(out), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        for path, seconds in parts:
            frames = b""
            if path is not None:
                with wave.open(str(path), "rb") as source:
                    if source.getframerate() != rate or source.getsampwidth() != 2:
                        raise ValueError(f"unexpected audio format in {path}")
                    frames = source.readframes(source.getnframes())
            total = round(seconds * rate) * 2
            target.writeframes(frames[:total] + b"\x00" * max(0, total - len(frames)))
    return out


def synthesize_scenes(texts: list[str], folder: Path) -> list[tuple[Path, list[dict[str, Any]]]]:
    """One continuous take, split at aligned word boundaries for the scene renderer."""
    whole = folder / "continuous.wav"
    result = synthesize("\n\n".join(texts), whole)
    if result is None:
        raise SystemExit("Continuous narration requires ELEVENLABS_API_KEY")
    _, words = result
    counts = [len(text.split()) for text in texts]
    if len(words) != sum(counts) or any(count == 0 for count in counts):
        raise SystemExit("ElevenLabs word alignment does not match the narration")
    if [w["word"] for w in words] != "\n\n".join(texts).split():
        raise SystemExit("ElevenLabs alignment changed the narration text")
    with wave.open(str(whole), "rb") as source:
        pcm = source.readframes(source.getnframes())
    boundaries = [0.0]
    at = 0
    for count in counts[:-1]:
        at += count
        boundaries.append((words[at - 1]["end"] + words[at]["start"]) / 2)
    boundaries.append(len(pcm) / (2 * RATE))
    pieces = []
    at = 0
    for index, count in enumerate(counts):
        start, end = boundaries[index : index + 2]
        path = folder / f"voice-{index}.wav"
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(RATE)
            target.writeframes(pcm[round(start * RATE) * 2 : round(end * RATE) * 2])
        said = [
            {**w, "start": round(w["start"] - start, 3), "end": round(w["end"] - start, 3)}
            for w in words[at : at + count]
        ]
        pieces.append((path, said))
        at += count
    whole.unlink()
    return pieces
