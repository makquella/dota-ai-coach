"""The player's own build on a hero: timings in wins vs losses, win rate with and without."""

from __future__ import annotations

from app.hero_build import hero_build


def _match(win: bool, items: list[tuple[str, int]], hero: str = "Juggernaut") -> dict:
    big = [{"item": name, "t": t} for name, t in items]
    return {
        "hero": hero,
        "hero_id": 8,
        "win": win,
        "analysis": {"sections": {"items": {"big_items": big}}},
    }


def _history() -> list[dict]:
    wins = [
        _match(True, [("Battle Fury", 900 + i * 30), ("Black King Bar", 1500)]) for i in range(4)
    ]
    losses = [
        _match(False, [("Battle Fury", 1200 + i * 30), ("Maelstrom", 1500)]) for i in range(3)
    ]
    other = [_match(True, [("Bottle", 300)], hero="Lina")] * 2
    unfinished = [_match(None, [("Battle Fury", 600)])]  # type: ignore[arg-type]
    return wins + losses + other + unfinished


def test_items_with_timings_and_win_rates_on_the_most_played_hero():
    build = hero_build(_history(), "ru")
    assert build["hero"] == "Juggernaut" and build["matches"] == 7 and build["wins"] == 4
    rows = {row["item"]: row for row in build["items"]}
    fury = rows["Battle Fury"]
    assert fury["games"] == 7 and fury["winrate"] == 57
    assert fury["t_win"] == 945 and fury["t_loss"] == 1230
    assert fury["winrate_without"] is None  # bought every game: nothing to compare
    bkb = rows["Black King Bar"]
    assert bkb["winrate"] == 100 and bkb["winrate_without"] == 0 and bkb["without_games"] == 3
    assert build["first_items"] == {"win": "Battle Fury", "loss": "Battle Fury"}
    assert "Battle Fury в победах у вас к 15:45, в поражениях — к 20:30." in build["highlights"]
    assert (
        "С Black King Bar вы выигрываете 100% (4 игры), без него — 0% (3 игры)."
        in build["highlights"]
    )


def test_needs_enough_finished_games_on_one_hero():
    assert hero_build(_history()[:5], "en") is None
    assert hero_build([], "en") is None
    english = hero_build(_history(), "en")
    assert (
        "With Black King Bar you win 100% (4 games), without it 0% (3 games)."
        in english["highlights"]
    )
