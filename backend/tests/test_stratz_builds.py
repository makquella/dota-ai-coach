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


def test_the_start_list_fits_in_the_starting_gold():
    keys = {1: "quelling_blade", 2: "tango", 3: "magic_stick", 4: "circlet", 5: "faerie_fire"}
    items = {
        "quelling_blade": {"cost": 100},
        "tango": {"cost": 90},
        "magic_stick": {"cost": 200},
        "circlet": {"cost": 155},
        "faerie_fire": {"cost": 65},
    }
    rows = [
        {"itemId": item_id, "instance": 0, "matchCount": 1000 - item_id * 10} for item_id in keys
    ]
    rows.append({"itemId": 2, "instance": 1, "matchCount": 900})  # a second Tango
    start = builder.start_items(rows, 1000, keys, items)
    total = sum(items[key]["cost"] * count for key, count in start)
    assert total <= builder.START_GOLD
    # The rarer buy that would go over 600 is left out, a cheaper later one kept.
    assert [key for key, _ in start] == ["quelling_blade", "tango", "magic_stick", "faerie_fire"]


def test_a_share_never_goes_over_the_games():
    # STRATZ counted Battle Fury in «140 %» of Juggernaut's games (another window
    # than the games): the most bought item stands in for the games then.
    keys = {1: "bfury", 2: "manta", 3: "black_king_bar"}
    items = {"bfury": {"cost": 4100}, "manta": {"cost": 4650}, "black_king_bar": {"cost": 4050}}
    rows = [
        {"itemId": 1, "instance": 0, "time": 14, "matchCount": 90, "winCount": 50},
        {"itemId": 1, "instance": 0, "time": 15, "matchCount": 50, "winCount": 25},
        {"itemId": 2, "instance": 0, "time": 21, "matchCount": 70, "winCount": 40},
        # 25 of 100 games by the raw count, 18 % of the purchases' own window.
        {"itemId": 3, "instance": 0, "time": 25, "matchCount": 25, "winCount": 12},
    ]
    build = builder.build_items(rows, 100, keys, items)
    assert [row[0] for row in build] == ["bfury", "manta"]
    assert [row[2] for row in build] == [100, 50]
    # Consistent counts keep the plain share.
    assert builder.share_base(1000, [600, 300]) == 1000


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


def test_the_bundled_file_is_sound():
    """The file the weekly workflow writes and the app ships. The workflow runs
    this before it opens its pull request: a PR opened with the workflow token
    starts no CI, so a broken export would otherwise reach main unchecked."""
    from app.stratz_builds import PATH

    data = json.loads(PATH.read_text(encoding="utf-8"))
    assert data["source"] == "STRATZ" and data["bracket"] == builder.BRACKET
    names = data["names"]
    assert all(isinstance(key, str) and isinstance(name, str) for key, name in names.items())
    heroes = data["heroes"]
    assert len(heroes) >= 100
    positions = {f"pos{n}" for n in range(1, 6)}
    for hero_id, entries in heroes.items():
        assert hero_id.isdigit() and set(entries) <= positions, hero_id
        for position, entry in entries.items():
            where = f"{hero_id} {position}"
            assert entry["games"] >= builder.MIN_GAMES and 0 <= entry["win"] <= 100, where
            for key, copies in entry["start"]:
                assert key in names and isinstance(copies, int) and copies >= 1, where
            minutes = [row[1] for row in entry["build"]]
            assert minutes == sorted(minutes), where
            assert len(entry["build"]) <= builder.BUILD_LIMIT, where
            for key, minute, share, win in entry["build"]:
                assert key in names, where
                assert 0 < minute <= 90 and 0 < share <= 100 and 0 <= win <= 100, where
    # A hero everyone plays is there with a start and a build.
    juggernaut = heroes["8"]["pos1"]
    assert juggernaut["start"] and juggernaut["build"]
