"""Recruitment alignment and private delivery fail closed before publishing."""

from __future__ import annotations

import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.promo import beta, beta_scenes, experiments, scenes  # noqa: E402


def test_master_take_scene_cuts_have_no_inserted_pauses_and_keep_every_word():
    texts = ["Play Dota?", "Give honest feedback."]
    words = scenes.estimated_words(" ".join(texts), 0.2, 29.0)
    timeline, captions, total = beta.timings(texts, words, 29.3)
    assert total == 30.5
    assert timeline[0]["end"] == timeline[1]["start"]
    assert timeline[-1]["end"] == total
    assert " ".join(c["text"] for c in captions) == " ".join(texts)
    assert captions[0]["start"] == 0.2
    assert "00:00:00,200" in beta.srt(captions)
    with pytest.raises(ValueError, match="shorten the script"):
        beta.timings(texts, words, 34.5)
    with pytest.raises(ValueError, match="exact narration"):
        beta.timings(["changed narration"], words, 29.3)


def test_both_scripts_match_source_claims_and_have_localized_final_calls_to_action():
    assert beta.verify_claims(online=False)["sources"]
    for language, keyword in (("uk", "БЕТА"), ("en", "BETA")):
        copy = beta_scenes.COPY[language]
        assert keyword in copy["voice"][-1]
        assert len(copy["voice"]) == len(copy["titles"]) == 7
        assert "Windows" in copy["free"]
        timeline, captions, _ = beta.storyboard(language)
        page = beta_scenes.page(language, timeline, captions)
        assert f'lang="{language}"' in page
        assert "data:image/" in page and "file://" not in page
        assert copy["site"] in page
        assert "0–4 000" in page
    english = " ".join(beta_scenes.COPY["en"]["voice"])
    assert not any("\u0400" <= char <= "\u04ff" for char in english)


@contextmanager
def telegram(chat_type="private"):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append((self.path, body))
            result = {"type": chat_type}
            if self.path.endswith("sendVideo"):
                result = {
                    "message_id": len(calls),
                    "chat": {"type": chat_type},
                    "video": {"width": 1080, "height": 1920, "duration": 32, "file_size": 24},
                }
            encoded = json.dumps({"ok": True, "result": result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
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


def pair(folder):
    for language in beta.LANGUAGES:
        target = folder / language
        target.mkdir()
        (target / "video.mp4").write_bytes(b"locally reviewed MP4")
        (target / "cover.jpg").write_bytes(b"cover")
        beta.save(target / "speech-check.json", {"ok": True, "language": language})
        beta.save(
            target / "package.json",
            {
                "kind": beta.KIND,
                "language": language,
                "draft": False,
                "seconds": 32,
                "layout": {"ok": True},
                "sha256": beta.digest(target / "video.mp4"),
                "voice_config": {"name": "Alex Nekrasov", "model": "eleven_v4"},
            },
        )


def test_actual_private_upload_returns_two_receipts_without_publishing(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "local-fixture-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1234")
    monkeypatch.setattr(beta, "media_check", lambda _path: {"ok": True})
    pair(tmp_path)
    with telegram() as (url, calls):
        monkeypatch.setattr(experiments, "TELEGRAM_API", url)
        beta.deliver(tmp_path)
        assert len(calls) == 3
        assert all("sendVideo" in route for route, _ in calls[1:])
        assert all(b"reply_markup" not in body and b"promo:all" not in body for _, body in calls)
        beta.deliver(tmp_path)
        assert len(calls) == 4  # getChat only; existing receipts prevent duplicate uploads.
    for language in beta.LANGUAGES:
        receipt = json.loads((tmp_path / language / "telegram-receipt.json").read_text())
        assert receipt["ok"] and receipt["message_id"] and receipt["chat_type"] == "private"
        assert "token" not in json.dumps(receipt)


def test_channel_or_altered_pair_is_rejected_before_any_video_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "local-fixture-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1234")
    monkeypatch.setattr(beta, "media_check", lambda _path: {"ok": True})
    pair(tmp_path)
    with telegram("channel") as (url, calls):
        monkeypatch.setattr(experiments, "TELEGRAM_API", url)
        with pytest.raises(SystemExit, match="private developer chat"):
            beta.deliver(tmp_path)
        assert len(calls) == 1
    (tmp_path / "en" / "video.mp4").write_bytes(b"unreviewed replacement")
    with telegram() as (url, calls):
        monkeypatch.setattr(experiments, "TELEGRAM_API", url)
        with pytest.raises(ValueError, match="integrity"):
            beta.deliver(tmp_path)
        assert len(calls) == 1
