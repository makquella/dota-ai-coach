"""Where the player dies over the last matches (Progress)."""

from __future__ import annotations

from app.advice_context import MAP_CENTER
from app.career_analysis import analyze_career
from app.career_deaths import MATCHES, death_map
from app.map_analysis import map_side

# Radiant's own jungle below the mid lane, and the enemy (Dire) jungle above it.
OWN_JUNGLE = (MAP_CENTER - 1500, MAP_CENTER - 3500)
ENEMY_JUNGLE = (MAP_CENTER + 1500, MAP_CENTER + 3500)


def _match(match_id, is_radiant, points, hero="Juggernaut"):
    deaths = []
    for t, (x, y) in points:
        deaths.append({"t": t, "x": x, "y": y, "side": map_side(x, y, is_radiant)})
    return {
        "match_id": match_id,
        "hero": hero,
        "hero_id": 8,
        "analysis": {"map": {"is_radiant": is_radiant, "deaths": deaths}},
    }


def _mirror(point):
    return (2 * MAP_CENTER - point[0], 2 * MAP_CENTER - point[1])


def test_dire_games_are_turned_so_the_player_is_always_radiant():
    matches = [
        _match(3, True, [(700, OWN_JUNGLE), (900, ENEMY_JUNGLE)]),
        # The same two places seen from Dire: the own jungle is top-right.
        _match(2, False, [(800, _mirror(OWN_JUNGLE)), (1000, _mirror(ENEMY_JUNGLE))]),
        _match(1, True, [(1200, OWN_JUNGLE)]),
    ]
    result = death_map(matches, "en")
    assert result["matches"] == 3 and result["total"] == 5 and result["per_match"] == 1.7
    own = [(d["x"], d["y"]) for d in result["deaths"] if d["side"] == "own"]
    assert own == [OWN_JUNGLE] * 3, "the Dire game's own-jungle death lands on the same spot"
    assert result["by_side"] == {"own": 3, "river": 0, "enemy": 2}
    assert result["enemy_share_late"] == 40
    spot = result["spots"][0]
    assert (spot["zone"], spot["side"], spot["count"], spot["matches"]) == ("jungle", "own", 3, 3)
    assert spot["label"]
    # Two enemy-jungle deaths are not a repeating place yet.
    assert len(result["spots"]) == 1


def test_a_spot_needs_deaths_from_two_matches():
    matches = [
        _match(2, True, [(700, OWN_JUNGLE), (800, OWN_JUNGLE), (900, OWN_JUNGLE)]),
        _match(1, True, [(700, ENEMY_JUNGLE), (800, ENEMY_JUNGLE)]),
    ]
    assert death_map(matches, "uk")["spots"] == []


def test_only_the_newest_matches_and_enough_deaths():
    many = [_match(i, True, [(700, OWN_JUNGLE)]) for i in range(MATCHES + 5, 0, -1)]
    result = death_map(many, "en")
    assert result["matches"] == MATCHES
    assert {d["match_id"] for d in result["deaths"]} == set(range(MATCHES + 5, 5, -1))
    assert death_map(many[:4], "en") is None, "under five deaths: nothing to show"
    # A review without a team side cannot be turned: left out.
    unknown = {**_match(99, True, [(700, OWN_JUNGLE)] * 6)}
    unknown["analysis"]["map"]["is_radiant"] = None
    assert death_map([unknown], "en") is None


def test_a_mapped_game_without_deaths_is_one_of_the_matches():
    matches = [
        _match(4, True, []),  # a clean game: in the window and the average
        _match(3, True, [(700, OWN_JUNGLE), (800, OWN_JUNGLE)]),
        _match(2, True, [(700, OWN_JUNGLE), (800, OWN_JUNGLE)]),
        _match(1, True, [(700, OWN_JUNGLE), (800, OWN_JUNGLE)]),
    ]
    result = death_map(matches, "en")
    assert result["matches"] == 4 and result["total"] == 6 and result["per_match"] == 1.5
    # The window is the newest mapped games, clean ones included.
    window = [_match(i, True, []) for i in range(MATCHES, 0, -1)]
    older = [_match(0, True, [(700, OWN_JUNGLE)] * 6)]
    assert death_map(window + older, "en") is None


def test_the_career_carries_it():
    matches = [
        {**_match(i, True, [(700, OWN_JUNGLE), (900, ENEMY_JUNGLE)]), "win": True}
        for i in range(4, 0, -1)
    ]
    career = analyze_career(matches, "uk")
    assert career["death_map"]["total"] == 8
    assert career["death_map"]["spots"][0]["label"]
