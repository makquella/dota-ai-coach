"""Actual Markdown files and HTTP scheduling prove cache/invalidation behavior."""

from __future__ import annotations

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import FrameType
from typing import Any

from fastapi.testclient import TestClient
from test_gsi_snapshot import _packet
from test_scheduler_spacing import _send_demo_state, _state

from app import main
from app.knowledge_base import KnowledgeBaseCache
from app.rag import KNOWLEDGE_BASE, retrieve_context


def test_actual_markdown_is_parsed_once_then_invalidated_by_edit_add_and_delete(
    tmp_path: Path,
) -> None:
    file = tmp_path / "a.md"
    file.write_text("First paragraph\n\nSecond paragraph", encoding="utf-8")
    cache = KnowledgeBaseCache(tmp_path, watch_changes=True)
    first = cache.paragraphs()
    assert first == ("First paragraph", "Second paragraph")
    assert cache.paragraphs() is first
    assert cache.health()["files_read"] == 1 and cache.health()["loads"] == 1
    before = file.stat().st_mtime_ns
    file.write_text("Edited", encoding="utf-8")
    os.utime(file, ns=(before + 1_000_000, before + 1_000_000))
    assert cache.paragraphs() == ("Edited",)
    other = tmp_path / "b.md"
    other.write_text("New document", encoding="utf-8")
    assert cache.paragraphs() == ("Edited", "New document")
    file.unlink()
    assert cache.paragraphs() == ("New document",)
    assert first == ("First paragraph", "Second paragraph")


def test_packaged_catalog_is_kept_and_bad_development_file_keeps_last_complete_value(
    tmp_path: Path,
) -> None:
    file = tmp_path / "a.md"
    file.write_text("Valid knowledge", encoding="utf-8")
    frozen = KnowledgeBaseCache(tmp_path, watch_changes=False)
    dev = KnowledgeBaseCache(tmp_path, watch_changes=True)
    assert frozen.paragraphs() == dev.paragraphs() == ("Valid knowledge",)
    file.write_bytes(b"\xff invalid private document")
    assert frozen.paragraphs() == dev.paragraphs() == ("Valid knowledge",)
    health = dev.health()
    assert health["failures"] == 1 and health["last_error"] == "UnicodeDecodeError"
    assert dev.paragraphs() == ("Valid knowledge",)
    assert dev.health()["failures"] == 1  # Backoff avoids repeating bad-file I/O.
    assert "private document" not in str(health)
    assert frozen.health()["files_read"] == 1


def test_concurrent_initial_readers_share_one_actual_file_read(tmp_path: Path) -> None:
    file = tmp_path / "a.md"
    file.write_text("Shared knowledge", encoding="utf-8")
    cache = KnowledgeBaseCache(tmp_path, watch_changes=True)
    entered, release = threading.Event(), threading.Event()
    previous = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is Path.read_text.__code__:
            if frame.f_locals.get("self") == file and not entered.is_set():
                sys.settrace(None)
                entered.set()
                assert release.wait(5)
        return None

    threading.settrace(trace)
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            pending = [executor.submit(cache.paragraphs)]
            try:
                assert entered.wait(5)
                assert cache.health()["loading"] is True
                pending.extend(executor.submit(cache.paragraphs) for _ in range(3))
            finally:
                release.set()
            assert [f.result(timeout=5) for f in pending] == [("Shared knowledge",)] * 4
    finally:
        release.set()
        threading.settrace(previous)
    assert cache.health()["files_read"] == 1 and cache.health()["loads"] == 1


def test_actual_live_and_demo_early_duplicate_paths_skip_retrieval(client: TestClient) -> None:
    calls = []
    previous = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is main._retrieve_rag_context.__code__:
            calls.append(threading.get_ident())
        return None

    threading.settrace(trace)
    try:
        assert client.post("/gsi", json=_packet()).status_code == 200
        first = client.get("/overlay/recommendation").json()
        assert first["new_advice"]
        count = len(calls)
        assert count == 1
        second = client.get("/overlay/recommendation").json()
        assert not second["new_advice"]
        assert len(calls) == count
        client.post("/session/reset")
        first = _send_demo_state(client, 1200, _state(1200))
        assert first["new_advice"]
        count = len(calls)
        assert count == 2
        second = _send_demo_state(client, 1205, _state(1205))
        assert not second["new_advice"]
        assert len(calls) == count
    finally:
        threading.settrace(previous)


def test_readers_keep_complete_catalog_during_actual_refresh_and_changed_files_retry(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    first.write_text("Old first", encoding="utf-8")
    second.write_text("Old second", encoding="utf-8")
    cache = KnowledgeBaseCache(tmp_path, watch_changes=True)
    old = cache.paragraphs()
    first.write_text("New first paragraph", encoding="utf-8")
    entered, release = threading.Event(), threading.Event()
    previous = threading.gettrace()

    def trace(frame: FrameType, event: str, _arg: Any) -> Any:
        if event == "call" and frame.f_code is Path.read_text.__code__:
            if frame.f_locals.get("self") == first and not entered.is_set():
                sys.settrace(None)
                entered.set()
                assert release.wait(5)
        return None

    threading.settrace(trace)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(cache.paragraphs)
            try:
                assert entered.wait(5)
                assert cache.paragraphs() is old
                second.write_text("New second paragraph", encoding="utf-8")
            finally:
                release.set()
            assert pending.result(timeout=5) == ("New first paragraph", "New second paragraph")
    finally:
        release.set()
        threading.settrace(previous)
    assert old == ("Old first", "Old second")
    assert cache.health()["loads"] == 2
    assert cache.health()["files_read"] == 6


def test_retrieval_keeps_owned_item_filter_and_returns_detached_lists(client: TestClient) -> None:
    query = "Anti-Mage farming Battle Fury before item"
    first = retrieve_context(query, hero="Anti-Mage")
    expected = list(first)
    first.clear()
    assert expected and retrieve_context(query, hero="Anti-Mage") == expected
    owned = retrieve_context(query, hero="Anti-Mage", owned_items=["Battle Fury"])
    assert all("before battle fury" not in p.lower() for p in owned)
    health = client.get("/diagnostics").json()["knowledge_base"]
    assert health == KNOWLEDGE_BASE.health()
    assert health["loaded"] and health["files_read"] > 0
