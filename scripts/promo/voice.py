"""The voice-over: Piper (offline neural TTS, MIT) with a Ukrainian voice.

One WAV per scene; the renderer times each scene by its voice. The model is
not in the repository (75 MB): the workflow downloads it once and caches it,
PROMO_VOICE_MODEL points at the .onnx file. Without a model (tests, a laptop
without Piper) `synthesize` returns None and the video is made silent; the
quality check refuses to send a silent video for approval."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from . import pronounce

# rhasspy/piper-voices: uk/uk_UA/ukrainian_tts/medium — speakers lada (0),
# mykyta (1), tetiana (2).
MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/ukrainian_tts/medium/"
    "uk_UA-ukrainian_tts-medium.onnx"
)
SPEAKER = int(os.environ.get("PROMO_VOICE_SPEAKER", "1"))
LENGTH_SCALE = os.environ.get("PROMO_VOICE_SPEED", "0.92")  # < 1: a little faster than default
SENTENCE_SILENCE = "0.25"


def model_path() -> Path | None:
    value = os.environ.get("PROMO_VOICE_MODEL", "")
    path = Path(value) if value else None
    return path if path and path.is_file() and path.with_suffix(".onnx.json").is_file() else None


def _piper() -> list[str] | None:
    exe = shutil.which("piper")
    if exe:
        return [exe]
    try:
        import piper  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "piper"]


def available() -> bool:
    return model_path() is not None and _piper() is not None


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / float(audio.getframerate())


def synthesize(text: str, out: Path) -> tuple[Path, list[str]] | None:
    """(the WAV, words read by the transliteration rules), or None without Piper."""
    model, command = model_path(), _piper()
    if model is None or command is None:
        return None
    spoken, guessed = pronounce.for_voice(text)
    subprocess.run(
        [
            *command,
            "--model",
            str(model),
            "--speaker",
            str(SPEAKER),
            "--length-scale",
            LENGTH_SCALE,
            "--sentence-silence",
            SENTENCE_SILENCE,
            "--output-file",
            str(out),
        ],
        input=spoken.encode("utf-8"),
        check=True,
        capture_output=True,
        timeout=300,
    )
    return out, guessed


def join(parts: list[tuple[Path | None, float]], out: Path, rate: int = 22050) -> Path:
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
