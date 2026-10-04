"""The weekly STRATZ export (scripts/build_stratz_builds.py) on a real answer:
Shadow Fiend in the Divine–Immortal bracket, mid (position 2)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import build_stratz_builds as builder  # noqa: E402

SAMPLE = json.loads((HERE / "stratz_sample.json").read_text(encoding="utf-8"))
KEYS = builder.by_id(SAMPLE["items"])


def test_the_mid_entry_has_the_start_and_the_build_in_order():
    entry = builder.hero_entry(SAMPLE["stratz"], KEYS, SAMPLE["items"])
    # Only position 2 was asked; position 1 has games but no item rows.
    assert set(entry) == {"pos2"}
    mid = entry["pos2"]
    assert mid["games"] == 3413 and mid["win"] == 44
    start = [key for key, _count in mid["start"]]
    assert {"tango", "faerie_fire", "enchanted_mango", "branches"} <= set(start)
    # A ward and the branch a support hands over are never a start buy.
    assert "ward_observer" not in start
    build = [row[0] for row in mid["build"]]
    minutes = [row[1] for row in mid["build"]]
    assert minutes == sorted(minutes)
    # Cheap parts never; the finished items in the order they come.
    assert "magic_wand" not in build and "circlet" not in build
    assert build.index("yasha_and_kaya") < build.index("black_king_bar")
    # Yasha and Kaya are the parts of Yasha and Kaya, not build lines of their own.
    assert "yasha" not in build and "kaya" not in build


def test_the_query_asks_every_position_for_one_hero():
    text = builder.query_text(11)
    for position in builder.POSITIONS:
        assert f"start_{position}:" in text and f"full_{position}:" in text
    assert "heroId: 11," in text and "$" not in text


def test_the_token_is_only_read_from_the_environment(monkeypatch, capsys):
    monkeypatch.delenv("STRATZ_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["build_stratz_builds.py"])
    assert builder.main() == 2
    assert "STRATZ_TOKEN is not set" in capsys.readouterr().err


def _reader(tmp_path, monkeypatch, data):
    from app import stratz_builds

    path = tmp_path / "stratz_builds.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(stratz_builds, "PATH", path)
    stratz_builds._data.cache_clear()
    return stratz_builds


READER_DATA = {
    "bracket": "DIVINE_IMMORTAL",
    "names": {"tango": "Tango", "branches": "Iron Branch", "blink": "Blink Dagger"},
    "heroes": {
        "11": {
            "pos2": {
                "games": 900,
                "win": 52,
                "start": [["branches", 2], ["tango", 1]],
                "build": [["blink", 17, 60, 55]],
            },
            "pos4": {"games": 200, "win": 48, "start": [["tango", 1]], "build": []},
        }
    },
}


def test_the_reader_picks_the_role_and_names_the_copies(tmp_path, monkeypatch):
    reader = _reader(tmp_path, monkeypatch, READER_DATA)
    try:
        start = reader.start_items(11, "Shadow Fiend", "mid")
        assert start[0] == {"key": "branches", "name": "Iron Branch ×2", "count": 2}
        assert reader.build(11, "Shadow Fiend", "mid")[0]["minute"] == 17
        # No role: the position the hero is played in most.
        assert reader.start_items(11, "Shadow Fiend", None)[0]["key"] == "branches"
        # A support: the support position present.
        assert [i["key"] for i in reader.start_items(11, "Shadow Fiend", "support")] == ["tango"]
        # A position nobody plays it in, an unknown hero: nothing.
        assert reader.start_items(11, "Shadow Fiend", "carry") == []
        assert reader.build(999, "Nobody", "mid") == [] and reader.build(None, "", "mid") == []
        assert reader.bracket() == "DIVINE_IMMORTAL"
    finally:
        reader._data.cache_clear()


def test_no_file_or_a_broken_one_means_nothing(tmp_path, monkeypatch):
    from app import stratz_builds

    monkeypatch.setattr(stratz_builds, "PATH", tmp_path / "missing.json")
    stratz_builds._data.cache_clear()
    try:
        assert stratz_builds.start_items(11, "Shadow Fiend", "mid") == []
        assert stratz_builds.bracket() is None
        broken = tmp_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(stratz_builds, "PATH", broken)
        stratz_builds._data.cache_clear()
        assert stratz_builds.build(11, "Shadow Fiend", "mid") == []
    finally:
        stratz_builds._data.cache_clear()
