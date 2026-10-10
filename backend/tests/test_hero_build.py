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
    build = hero_build(_history(), "uk")
    assert build["hero"] == "Juggernaut" and build["matches"] == 7 and build["wins"] == 4
    rows = {row["item"]: row for row in build["items"]}
    fury = rows["Battle Fury"]
    assert fury["games"] == 7 and fury["winrate"] == 57
    assert fury["t_win"] == 945 and fury["t_loss"] == 1230
    assert fury["winrate_without"] is None  # bought every game: nothing to compare
    bkb = rows["Black King Bar"]
    assert bkb["winrate"] == 100 and bkb["winrate_without"] == 0 and bkb["without_games"] == 3
    assert build["first_items"] == {"win": "Battle Fury", "loss": "Battle Fury"}
    assert "Battle Fury у перемогах у вас до 15:45, у поразках — до 20:30." in build["highlights"]
    assert (
        "З Black King Bar ви виграєте 100% (4 гри), без нього — 0% (3 гри)." in build["highlights"]
    )


def test_the_key_item_timing_game_by_game():
    # Newest first, as the career reads them: Battle Fury comes sooner lately.
    times = [840, 870, 900, 930, 960, 1080, 1110, 1140, 1170, 1200]
    games = [
        {**_match(i % 3 != 0, [("Power Treads", 480), ("Battle Fury", t)]), "match_id": 100 - i}
        for i, t in enumerate(times)
    ]
    trend = hero_build(games, "en")["timing_trend"]
    assert trend["item"] == "Battle Fury", "Power Treads at 8:00 is not the key item"
    assert [p["t"] for p in trend["points"]] == list(reversed(times))
    assert trend["points"][-1] == {"match_id": 100, "t": 840, "win": False}
    assert (trend["recent"], trend["before"], trend["change"]) == (900, 1140, -240)
    assert trend["recent_games"] == 5 and trend["before_games"] == 5


def test_the_timing_trend_needs_games_before_to_compare():
    games = [_match(True, [("Battle Fury", 900 + i * 10)]) for i in range(6)]
    trend = hero_build(games, "en")["timing_trend"]
    assert trend["recent"] == 920 and "change" not in trend
    early = [_match(True, [("Power Treads", 400 + i)]) for i in range(6)]
    assert hero_build(early, "en")["timing_trend"] is None


def test_needs_enough_finished_games_on_one_hero():
    assert hero_build(_history()[:5], "en") is None
    assert hero_build([], "en") is None
    english = hero_build(_history(), "en")
    assert (
        "With Black King Bar you win 100% (4 games), without it 0% (3 games)."
        in english["highlights"]
    )
