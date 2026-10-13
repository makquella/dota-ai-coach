"""The voice-over: ElevenLabs (multilingual model), the script's Ukrainian with
the English hero and ability names read as they are.

One WAV per scene (16-bit mono PCM, RATE), and the time of every word from
ElevenLabs' character alignment: the subtitles light up word by word with the
voice. Neighbouring scenes go along as `previous_text` / `next_text`, so the
intonation runs on across cuts.

Environment: ELEVENLABS_API_KEY (a repository secret), ELEVENLABS_VOICE_ID and
ELEVENLABS_MODEL (optional). Without the key `synthesize` returns None and
the video is made silent; the quality check refuses to send a silent video
for approval. The key is never printed."""

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
# A premade voice that every account has; a native Ukrainian voice from the
# Voice Library sounds better: put its id into the ELEVENLABS_VOICE_ID variable.
DEFAULT_VOICE = "TX3LPaxmHKxFdv7VOQHJ"  # "Liam"
DEFAULT_MODEL = "eleven_multilingual_v2"
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


def _post(url: str, body: dict[str, Any], key: str) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    for pause in (*RETRIES, None):
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "xi-api-key": key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
                return dict(json.loads(response.read()))
        except urllib.error.HTTPError as error:
            detail = error.read(300).decode("utf-8", "replace").strip()
            if error.code in (429, 500, 502, 503, 504) and pause is not None:
                time.sleep(pause)
                continue
            raise SystemExit(f"ElevenLabs: HTTP {error.code} {detail}") from None
        except (urllib.error.URLError, TimeoutError) as error:
            if pause is not None:
                time.sleep(pause)
                continue
            raise SystemExit(f"ElevenLabs: {error}") from None
    raise SystemExit("ElevenLabs: no answer")


def synthesize(
    text: str, out: Path, previous: str = "", following: str = ""
) -> tuple[Path, list[dict[str, Any]]] | None:
    """(the WAV, its words with times), or None without an API key."""
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return None
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE
    body: dict[str, Any] = {
        "text": text,
        "model_id": os.environ.get("ELEVENLABS_MODEL", "").strip() or DEFAULT_MODEL,
        "voice_settings": SETTINGS,
    }
    if previous:
        body["previous_text"] = previous
    if following:
        body["next_text"] = following
    answer = _post(API.format(voice=voice), body, key)
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
