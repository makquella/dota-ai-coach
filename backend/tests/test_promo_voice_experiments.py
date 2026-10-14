"""Real local provider HTTP, PCM files, and Telegram preview delivery."""

from __future__ import annotations

import base64
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.promo import experiments, voice  # noqa: E402


@contextmanager
def _provider() -> Iterator[tuple[str, list[tuple[str, bytes | None]]]]:
    calls: list[tuple[str, bytes | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            calls.append((self.path, None))
            if self.path.startswith("/v1/models"):
                result = [
                    {"model_id": "eleven_multilingual_v2", "can_do_text_to_speech": True},
                    {"model_id": "eleven_v3", "can_do_text_to_speech": True},
                ]
            else:
                result = {
                    "voices": [
                        {
                            "voice_id": str(i),
                            "name": f"Native {i}",
                            "labels": {"language": "uk", "gender": "male"},
                        }
                        for i in range(3)
                    ]
                    + [
                        {
                            "voice_id": "english",
                            "name": "English",
                            "labels": {"language": "en", "gender": "male"},
                            "verified_languages": [{"language": "uk"}],
                        }
                    ]
                }
            self._answer(result)

        def do_POST(self) -> None:
            data = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append((self.path, data))
            if self.path.endswith("/sendVideo"):
                self._answer({"ok": True, "result": {"message_id": 42}})
                return
            body = json.loads(data)
            text = body["text"]
            step = 0.015
            frames = round(len(text) * step * voice.RATE)
            self._answer(
                {
                    "audio_base64": base64.b64encode(b"\x10\x00" * frames).decode(),
                    "alignment": {
                        "characters": list(text),
                        "character_start_times_seconds": [i * step for i in range(len(text))],
                        "character_end_times_seconds": [(i + 1) * step for i in range(len(text))],
                    },
                }
            )

        def _answer(self, result: Any) -> None:
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, _format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def test_actual_catalog_selects_modern_model_and_native_male_voices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    with _provider() as (url, calls):
        monkeypatch.setattr(experiments, "CATALOG_API", url)
        selected = experiments.catalog()
    assert selected["model"] == "eleven_v3" and not selected["v4_available"]
    assert len(selected["voices"]) == 3
    assert all(v["name"].startswith("Native") for v in selected["voices"])
    assert len(calls) == 2
    assert (
        experiments.modern_model([{"model_id": "eleven_v4", "can_do_text_to_speech": True}])
        == "eleven_v4"
    )
    with pytest.raises(SystemExit, match="no legacy fallback"):
        experiments.modern_model(
            [{"model_id": "eleven_multilingual_v2", "can_do_text_to_speech": True}]
        )


def test_continuous_take_uses_one_real_request_and_preserves_scene_word_times(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_MODEL", "eleven_v3")
    monkeypatch.setenv("ELEVENLABS_LANGUAGE", "uk")
    monkeypatch.setenv("ELEVENLABS_STABILITY", "0.5")
    texts = ["Проти Phantom Lancer.", "Wardly підказує Maelstrom."]
    with _provider() as (url, calls):
        monkeypatch.setattr(voice, "API", url + "/v1/tts/{voice}")
        pieces = voice.synthesize_scenes(texts, tmp_path)
    assert len(calls) == 1
    request = json.loads(calls[0][1])
    assert request["model_id"] == "eleven_v3" and request["language_code"] == "uk"
    assert request["voice_settings"] == {"stability": 0.5}
    assert "previous_text" not in request and "next_text" not in request
    for (path, words), text in zip(pieces, texts, strict=True):
        assert [w["word"] for w in words] == text.split()
        assert 0 <= words[0]["start"] < words[-1]["end"] <= voice.duration(path) + 0.002
    assert not (tmp_path / "continuous.wav").exists()


def test_preview_delivery_is_real_bot_upload_without_publish_callbacks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "preview-test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    (tmp_path / "video.mp4").write_bytes(b"video-fixture")
    profile = {
        "variant": "A",
        "name": "Native & Voice",
        "delivery": "природна",
        "model": "eleven_v3",
        "stability": 0.5,
        "speed": 1.0,
    }
    with _provider() as (url, calls):
        monkeypatch.setattr(experiments, "TELEGRAM_API", url)
        message = experiments.send_preview(tmp_path, {"seconds": 22.0}, profile)
    assert message == 42 and len(calls) == 1
    assert calls[0][0] == "/botpreview-test-token/sendVideo"
    assert b"video-fixture" in calls[0][1] and b"Native &amp; Voice" in calls[0][1]
    assert b"reply_markup" not in calls[0][1] and b"promo:all" not in calls[0][1]
