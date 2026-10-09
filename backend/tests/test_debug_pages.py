"""Legacy browser pages are debug-only: /debug/ in a source checkout, nothing
else of frontend/ (the launcher's sources) is served, none in the frozen app."""

from __future__ import annotations


def test_debug_pages_are_served_and_marked(client):
    for path in ("/debug/", "/debug/overlay.html"):
        page = client.get(path)
        assert page.status_code == 200
        assert "Debug page for developers" in page.text
    assert client.get("/debug/script.js").status_code == 200


def test_the_launcher_sources_are_not_served(client):
    for path in ("/frontend/", "/frontend/launcher/main.js", "/frontend/index.html"):
        assert client.get(path).status_code == 404


def test_the_pages_load_without_a_token_but_the_api_does_not(client):
    """The pages ask for the token themselves; only they are public."""
    anonymous = {"Authorization": ""}
    assert client.get("/debug/", headers=anonymous).status_code == 200
    assert client.get("/frontend/launcher/main.js", headers=anonymous).status_code == 401


def test_the_frozen_app_has_no_debug_pages(tmp_path):
    from app.main import DEBUG_PAGES_DIR, debug_pages_dir

    assert debug_pages_dir(frozen=False) == DEBUG_PAGES_DIR
    assert debug_pages_dir(frozen=True) is None
    assert debug_pages_dir(frozen=False, directory=tmp_path / "missing") is None
