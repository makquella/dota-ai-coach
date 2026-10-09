"""Trusted local HTTP clients and untrusted requests exercise the real app."""

from __future__ import annotations

import copy
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import diagnostics
from app.config import BACKEND_PORT
from app.gsi_state import get_gsi_debug_latest
from app.live_session_recorder import LIVE_SESSION_RECORDER
from app.local_api_auth import AUTH_FILE, LOCAL_API_AUTH, LOCAL_API_URL, load_auth
from app.local_api_security import BODY_LIMIT, LocalApiSecurity
from app.main import app
from app.match_memory import MATCH_MEMORY
from app.match_records import MATCH_RECORDS
from app.player_api import PLAYER_SERVICE


def _raw_client(application: Any = app) -> TestClient:
    return TestClient(application, base_url=LOCAL_API_URL, client=("127.0.0.1", 50000))


def _payload(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / "data/gsi_samples/real_player_ranked.json").read_text())


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/session/reset", {}),
        ("POST", "/settings/advice", {"frequency": "quiet"}),
        ("POST", "/player/link", {"steam": "123"}),
        (
            "POST",
            "/player/backup",
            {"format": "wardly-backup", "version": 1, "account_id": 123, "tables": {}},
        ),
        ("DELETE", "/player", None),
        ("GET", "/player", None),
        ("GET", "/diagnostics", None),
        ("GET", "/gsi/debug/latest", None),
        ("GET", "/state/current", None),
        ("GET", "/overlay/recommendation", None),
        ("GET", "/match-records", None),
    ],
)
def test_missing_control_token_cannot_read_or_mutate_private_state(
    method: str, path: str, body: Any
) -> None:
    MATCH_MEMORY.last_advice_type = "KEEP"
    response = _raw_client().request(method, path, json=body)
    assert response.status_code == 401 and response.json()["code"] == "unauthorized"
    assert MATCH_MEMORY.last_advice_type == "KEEP"
    assert PLAYER_SERVICE.store.primary_account_id() is None


@pytest.mark.parametrize(
    "origin", ["https://audit.invalid", "null", "http://localhost:5173", "http://127.0.0.1:3000"]
)
def test_untrusted_origin_is_rejected_even_with_a_valid_control_token(
    client: TestClient, repo_root: Path, origin: str
) -> None:
    assert client.post("/gsi", json=_payload(repo_root)).status_code == 200
    before = copy.deepcopy(get_gsi_debug_latest())
    memory = MATCH_MEMORY.last_advice_type
    for path in ("/gsi", "/session/reset"):
        response = client.post(
            path,
            content=json.dumps(_payload(repo_root)),
            headers={"Origin": origin, "Content-Type": "text/plain"},
        )
        assert response.status_code == 403 and response.json()["code"] == "untrusted_origin"
        assert "access-control-allow-origin" not in response.headers
    assert get_gsi_debug_latest() == before
    assert MATCH_MEMORY.last_advice_type == memory


@pytest.mark.parametrize(
    "host",
    [
        "audit.invalid",
        "audit.invalid:8000",
        "127.0.0.1:3000",
        "localhost.evil.invalid:8000",
        "127.0.0.1.:8000",
        "127.0.0.1:8000@evil.invalid",
    ],
)
def test_wrong_authority_is_rejected_before_a_control_operation(
    client: TestClient, host: str
) -> None:
    MATCH_MEMORY.last_advice_type = "KEEP"
    response = client.post("/session/reset", headers={"Host": host})
    assert response.status_code == 400 and response.json()["code"] == "invalid_host"
    assert MATCH_MEMORY.last_advice_type == "KEEP"


def test_remote_peer_and_duplicate_authority_or_credentials_are_rejected() -> None:
    remote = TestClient(
        app, base_url=LOCAL_API_URL, headers=LOCAL_API_AUTH.headers, client=("192.0.2.1", 50000)
    )
    assert remote.get("/player").status_code == 403
    raw = _raw_client()
    for headers, code in [
        (
            [("Host", f"127.0.0.1:{BACKEND_PORT}"), ("Host", f"localhost:{BACKEND_PORT}")],
            "invalid_host",
        ),
        ([("Origin", LOCAL_API_URL), ("Origin", "https://audit.invalid")], "untrusted_origin"),
        (
            [
                ("Authorization", f"Bearer {LOCAL_API_AUTH.control}"),
                ("Authorization", "Bearer wrong"),
            ],
            "unauthorized",
        ),
    ]:
        assert raw.get("/player", headers=headers).json()["code"] == code


def test_gsi_capability_accepts_dota_but_never_authorizes_control(repo_root: Path) -> None:
    raw = _raw_client()
    payload = _payload(repo_root)
    payload["auth"] = {"token": LOCAL_API_AUTH.gsi}
    accepted = raw.post("/gsi", json=payload)
    assert accepted.status_code == 200 and accepted.json()["state"]["hero"]
    assert "auth" not in get_gsi_debug_latest()["latest_raw_payload"]
    before = copy.deepcopy(get_gsi_debug_latest())
    for token in (None, LOCAL_API_AUTH.control, "wrong", [LOCAL_API_AUTH.gsi]):
        payload["auth"] = {"token": token}
        assert raw.post("/gsi", json=payload).status_code == 401
    for path in ("/player", "/diagnostics"):
        assert (
            raw.get(path, headers={"Authorization": f"Bearer {LOCAL_API_AUTH.gsi}"}).status_code
            == 401
        )
    assert (
        raw.post(
            "/session/reset", headers={"Authorization": f"Bearer {LOCAL_API_AUTH.gsi}"}
        ).status_code
        == 401
    )
    assert raw.get(f"/player?token={LOCAL_API_AUTH.control}").status_code == 401
    assert get_gsi_debug_latest() == before


def test_trusted_manual_tools_and_cors_preflight_remain_supported(
    client: TestClient, repo_root: Path
) -> None:
    assert client.post("/gsi", json=_payload(repo_root)).status_code == 200
    assert (
        client.post(
            "/session/reset", headers={"Authorization": f"bearer {LOCAL_API_AUTH.control}"}
        ).status_code
        == 200
    )
    assert _raw_client().get("/health").status_code == 200
    assert _raw_client().get("/docs").status_code == 200
    schema = _raw_client().get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["LocalControl"]["scheme"] == "bearer"
    assert schema["paths"]["/player"]["get"]["security"] == [{"LocalControl": []}]
    preflight = _raw_client().options(
        "/player",
        headers={
            "Origin": LOCAL_API_URL,
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == LOCAL_API_URL
    assert (
        _raw_client()
        .options(
            "/player",
            headers={"Origin": "https://audit.invalid", "Access-Control-Request-Method": "POST"},
        )
        .status_code
        == 403
    )


@pytest.mark.parametrize(
    ("content", "headers", "code"),
    [
        ("{}", {"Content-Type": "text/plain"}, "json_required"),
        ("{}", {"Content-Type": "application/x-www-form-urlencoded"}, "json_required"),
        (
            "{}",
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
            "unsupported_encoding",
        ),
        ("{", {"Content-Type": "application/json"}, "invalid_json"),
        ("[]", {"Content-Type": "application/json"}, "invalid_gsi"),
        ('{"auth":{"token":NaN}}', {"Content-Type": "application/json"}, "invalid_json"),
    ],
)
def test_gsi_body_checks_happen_before_the_live_pipeline(
    client: TestClient, content: str, headers: dict[str, str], code: str
) -> None:
    assert client.post("/gsi", content=content, headers=headers).json()["code"] == code
    assert get_gsi_debug_latest()["latest_raw_payload"] is None


def test_body_limits_cover_actual_streams_and_declared_lengths() -> None:
    application = LocalApiSecurity(
        app, auth=LOCAL_API_AUTH, port=BACKEND_PORT, limits={"/gsi": 256, "/player/backup": 512}
    )
    raw = _raw_client(application)
    for path, content in [
        ("/gsi", [b"{" + b" " * 200, b" " * 200 + b"}"]),
        ("/player/backup", [b" " * 400, b" " * 400]),
    ]:
        response = raw.post(
            path,
            content=iter(content),
            headers={"Content-Type": "application/json", **LOCAL_API_AUTH.headers},
        )
        assert response.status_code == 413 and response.json()["code"] == "body_too_large"
    for length in ("-1", "not-a-number", "9" * 20):
        assert (
            raw.post("/gsi", content=b"{}", headers={"Content-Length": length}).json()["code"]
            == "invalid_length"
        )
    assert (
        raw.post(
            "/player/backup", content=b"", headers={"Content-Length": str(513 * 1024 * 1024)}
        ).status_code
        == 413
    )
    assert PLAYER_SERVICE.store.primary_account_id() is None


def test_gsi_token_never_reaches_debug_recordings_recovery_or_backups(
    client: TestClient, tmp_path: Path, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    LIVE_SESSION_RECORDER.stop()
    monkeypatch.setattr(LIVE_SESSION_RECORDER, "base_dir", tmp_path / "sessions")
    MATCH_RECORDS.configure(tmp_path / "matches", enabled=True)
    assert client.post("/session-recording/start").status_code == 200
    payload = _payload(repo_root)
    payload["auth"] = {"token": LOCAL_API_AUTH.gsi}
    try:
        assert _raw_client().post("/gsi", json=payload).status_code == 200
        PLAYER_SERVICE.tracker.flush()
        assert "auth" not in get_gsi_debug_latest()["latest_raw_payload"]
        for path in ("/gsi/debug/latest", "/diagnostics", "/player/backup"):
            body = client.get(path).text
            assert LOCAL_API_AUTH.gsi not in body and LOCAL_API_AUTH.control not in body
    finally:
        LIVE_SESSION_RECORDER.stop()
        MATCH_RECORDS.flush()
        MATCH_RECORDS.set_enabled(False)
    files = [p for p in tmp_path.rglob("*") if p.is_file() and p.suffix in {".json", ".jsonl"}]
    assert any(p.name == "raw_gsi_states.jsonl" for p in files)
    for path in files:
        assert LOCAL_API_AUTH.gsi not in path.read_text()
    assert LOCAL_API_AUTH.gsi not in diagnostics.redact(f'"token" "{LOCAL_API_AUTH.gsi}"')


def test_credentials_are_atomic_private_and_stable_across_concurrent_loads(tmp_path: Path) -> None:
    tmp_path = tmp_path / "credentials"
    barrier = threading.Barrier(8)
    results: list[Any] = []
    errors: list[BaseException] = []

    def load() -> None:
        try:
            barrier.wait(5)
            results.append(load_auth(tmp_path, {}))
        except BaseException as error:
            errors.append(error)

    threads = [threading.Thread(target=load) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
    assert not errors and len(results) == 8
    assert all(auth == results[0] for auth in results)
    assert results[0].control != results[0].gsi
    assert list(tmp_path.iterdir()) == [tmp_path / AUTH_FILE]
    assert results[0].control not in repr(results[0])
    if os.name != "nt":
        assert (tmp_path / AUTH_FILE).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "data", ["not json", '{"version":true}', '{"version":1,"control":"private","gsi":"private"}']
)
def test_bad_credentials_fail_closed_without_replacing_the_file(tmp_path: Path, data: str) -> None:
    path = tmp_path / AUTH_FILE
    path.write_text(data)
    with pytest.raises(ValueError) as error:
        load_auth(tmp_path, {})
    assert "private" not in str(error.value)
    assert path.read_text() == data


def test_partial_environment_or_equal_tokens_fail_closed(tmp_path: Path) -> None:
    token = secrets.token_hex(32)
    for environment in (
        {"DOTA_AI_CONTROL_TOKEN": token},
        {"DOTA_AI_GSI_TOKEN": token},
        {"DOTA_AI_CONTROL_TOKEN": token, "DOTA_AI_GSI_TOKEN": token},
    ):
        with pytest.raises(ValueError):
            load_auth(tmp_path, environment)
    assert not (tmp_path / AUTH_FILE).exists()


def test_real_tcp_backend_enforces_capabilities_and_stream_limits(
    tmp_path: Path, repo_root: Path
) -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {
        **os.environ,
        "DOTA_AI_BACKEND_PORT": str(port),
        "DOTA_AI_BACKEND_HOST": "127.0.0.1",
        "DOTA_AI_BACKEND_STDIN_CONTROL": "1",
        "OPENDOTA_ENABLED": "false",
        "PLAYER_DATA_DIR": str(tmp_path / "player"),
        "SESSION_RECORDS_DIR": str(tmp_path / "sessions"),
    }
    with (tmp_path / "backend.log").open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-u", "packaging/backend_server.py"],
            cwd=repo_root / "backend",
            env=env,
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=3) as wire:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if wire.get("/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert process.poll() is None and time.monotonic() < deadline
                    threading.Event().wait(0.05)
                assert wire.post("/session/reset").status_code == 401
                payload = _payload(repo_root)
                payload["auth"] = {"token": LOCAL_API_AUTH.gsi}
                assert wire.post("/gsi", json=payload).status_code == 200
                assert (
                    wire.get(
                        "/player", headers={"Authorization": f"Bearer {LOCAL_API_AUTH.gsi}"}
                    ).status_code
                    == 401
                )
                assert (
                    wire.post(
                        "/session/reset",
                        content=iter([b" " * BODY_LIMIT, b" "]),
                        headers={"Content-Type": "application/json", **LOCAL_API_AUTH.headers},
                    ).status_code
                    == 413
                )
                assert wire.get("/gsi/debug/latest", headers=LOCAL_API_AUTH.headers).json()[
                    "latest_raw_payload"
                ]["hero"]
                from scripts.run_overlay_demo import _get_json, _post_json

                assert isinstance(_get_json(f"{wire.base_url}/player")["linked"], bool)
                assert _post_json(f"{wire.base_url}/session/reset", {})["status"] == "ok"
        finally:
            if process.stdin is not None:
                process.stdin.write(b"shutdown\n")
                process.stdin.close()
            try:
                assert process.wait(timeout=10) == 0
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)


def test_replay_helper_does_not_forward_credentials_on_redirect() -> None:
    from scripts.run_overlay_demo import _get_json, _post_json

    received: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/target")
            else:
                received.append(self.headers.get("Authorization"))
                self.send_response(200)
            self.end_headers()

        def do_POST(self) -> None:
            self.do_GET()

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/redirect"
        with pytest.raises(SystemExit, match="Backend error 302"):
            _get_json(url)
        with pytest.raises(SystemExit, match="Backend error 302"):
            _post_json(url, {})
        assert received == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
