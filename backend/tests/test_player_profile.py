"""The «Профіль» tab: rating graph, app level, achievements, sparks (app/player_profile.py)."""

from __future__ import annotations

from app.player_profile import (
    MMR_STEP,
    TIER_SPARKS,
    XP_GAME,
    XP_WIN,
    achievements,
    add_anchor,
    build_profile,
    level_of,
    load_anchors,
    medal_mmr,
    rating,
)

DAY = 86400
T0 = 1_780_000_000


def _row(i, *, win=True, ranked=True, app=True, score=None, hero_id=8, deaths=3, duration=2400):
    return {
        "match_id": 1000 + i,
        "start_time": T0 + i * DAY,
        "duration": duration,
        "hero_id": hero_id,
        "win": win,
        "deaths": deaths,
        "lobby_type": 7 if ranked else 0,
        "score": score,
        "has_analysis": score is not None,
        "sources": ["gsi", "opendota"] if app else ["opendota"],
    }


def test_the_rating_counts_forwards_and_backwards_from_the_typed_mmr():
    rows = [_row(0, win=True), _row(1, win=False), _row(2, win=True), _row(3, win=True)]
    # Typed in after the second match: 3000.
    anchors = load_anchors(add_anchor(None, 3000, T0 + DAY + 3600))
    graph = rating(rows, anchors, None, T0 + 10 * DAY)
    games = [p for p in graph["points"] if "win" in p]
    assert [p["mmr"] for p in games] == [
        3000 + MMR_STEP,
        3000,
        3000 + MMR_STEP,
        3000 + 2 * MMR_STEP,
    ]
    assert graph["current"] == 3050 and graph["source"] == "manual"
    assert graph["peak"] == 3050 and graph["lowest"] == 3000
    assert graph["wins_20"] == 3 and graph["losses_20"] == 1
    # Four games: +25 -25 +25 +25 from where it was before the first one.
    assert graph["change_20"] == 2 * MMR_STEP
    # Unranked games never move it.
    assert rating([_row(0, ranked=False)], anchors, None, T0)["games"] == 0


def test_a_new_typed_mmr_resets_the_line():
    rows = [_row(0), _row(1), _row(3)]
    raw = add_anchor(None, 2000, T0 - 3600)
    raw = add_anchor(raw, 2500, T0 + 2 * DAY)  # corrected after the second game
    graph = rating(rows, load_anchors(raw), None, T0 + 10 * DAY)
    assert graph["current"] == 2500 + MMR_STEP
    assert [p for p in graph["points"] if p.get("anchor")][-1]["mmr"] == 2500


def test_without_a_typed_mmr_the_medal_gives_a_rough_start():
    assert medal_mmr(11) == 77  # Herald 1, the middle of its first star
    assert medal_mmr(54) == (4 * 5 + 3) * 154 + 77  # Legend (the 5th medal), 4 stars
    assert medal_mmr(80) == 5620
    assert medal_mmr(None) is None and medal_mmr(55 + 1) is None
    graph = rating([_row(0), _row(1, win=False)], [], 54, T0 + 10 * DAY)
    assert graph["source"] == "medal" and graph["current"] == medal_mmr(54)
    assert not any(p.get("anchor") for p in graph["points"])
    assert rating([_row(0)], [], None, T0) is None


def test_bad_anchors_are_ignored():
    assert load_anchors('[{"at": 1, "mmr": -5}, {"at": "x", "mmr": 3000}, 7]') == []
    assert load_anchors("not json") == []


def test_levels_cost_more_each_time():
    assert level_of(0) == {"level": 1, "xp": 0, "into": 0, "need": 300}
    assert level_of(299)["level"] == 1
    assert level_of(300)["level"] == 2 and level_of(300)["need"] == 400
    assert level_of(700)["level"] == 3


def test_achievements_count_matches_with_the_app_only():
    rows = [_row(i, win=i % 4 != 3, score=75 if i < 3 else None) for i in range(12)]
    rows.append(_row(20, app=False))  # fetched from OpenDota only
    profile = build_profile(
        list(reversed(rows)), player={"rank_tier": 54}, mmr_raw=None, lang="uk", now=T0
    )
    stats = profile["stats"]
    assert stats["app_games"] == 12 and stats["all_games"] == 13
    badges = {b["id"]: b for b in profile["achievements"]}
    games = badges["app_games"]
    assert games["tier"] == 2 and games["tier_name"] == "Срібло" and games["target"] == 50
    assert games["text"] == "Зіграйте 50 матчів з Wardly"
    assert badges["app_wins"]["text"] == "Виграйте 10 матчів з Wardly"
    assert badges["win_streak"]["text"] == "Виграйте 5 матчів поспіль з Wardly"
    assert badges["few_deaths"]["text"].startswith("Зіграйте 1 матч від 20 хвилин")
    assert badges["weeks"]["text"] == "Хоча б матч на тиждень з Wardly: 4 тижні"
    assert games["unlocked"][1]["at"] == T0 + 9 * DAY  # the tenth match
    assert badges["win_streak"]["value"] == 3 and badges["win_streak"]["tier"] == 1
    assert badges["good_games"]["value"] == 3
    assert badges["hero_master"]["value"] == 12 and badges["hero_master"]["tier"] == 1
    wins = sum(1 for r in rows[:12] if r["win"])
    good = 3
    assert profile["level"]["xp"] == 12 * XP_GAME + wins * XP_WIN + good * 25
    tier_sparks = sum(sum(TIER_SPARKS[: b["tier"]]) for b in profile["achievements"])
    assert profile["sparks"]["earned"] == 12 * 10 + wins * 5 + tier_sparks
    assert profile["player"]["rank_label"] == "Легенда 4"


def test_spent_sparks_come_off_the_balance():
    rows = [_row(i) for i in range(3)]
    owned = '{"owned": ["frame_arcana", "title_legend"], "equipped": {}}'
    profile = build_profile(rows, player=None, mmr_raw=None, cosmetics_raw=owned, lang="en", now=T0)
    assert profile["sparks"]["spent"] == 5500
    assert profile["sparks"]["balance"] == 0 and profile["rating"] is None


def test_mmr_gain_is_an_achievement():
    badges, sparks = achievements([], 160, "en")
    gain = next(b for b in badges if b["id"] == "mmr_gain")
    assert gain["tier"] == 2 and sparks == TIER_SPARKS[0] + TIER_SPARKS[1]


def test_the_profile_through_the_api(client):
    from match_fixtures import ME, FakeOpenDota

    from app.player_api import PLAYER_SERVICE

    assert client.get("/player/profile").json() == {"profile": None}
    PLAYER_SERVICE.configure(PLAYER_SERVICE.data_dir, client=FakeOpenDota(), auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    body = client.get("/player/profile?lang=uk").json()["profile"]
    assert body["level"]["level"] == 1 and len(body["achievements"]) >= 8
    assert client.post("/player/profile/mmr", json={"mmr": 99999}).status_code == 400
    body = client.post("/player/profile/mmr?lang=uk", json={"mmr": 3200}).json()["profile"]
    assert body["rating"]["source"] == "manual" and body["rating"]["current"] >= 0
    body = client.delete("/player/profile/mmr").json()["profile"]
    assert body["rating"] is None or body["rating"]["source"] == "medal"


def test_plurals():
    from app.player_profile import MATCH_EN, MATCH_UK, plural

    assert [plural(n, MATCH_UK, "uk") for n in (1, 2, 5, 11, 21, 22, 112)] == [
        "матч",
        "матчі",
        "матчів",
        "матчів",
        "матч",
        "матчі",
        "матчів",
    ]
    assert plural(1, MATCH_EN, "en") == "match" and plural(3, MATCH_EN, "en") == "matches"


def test_the_public_card_shows_no_account_and_the_mmr_only_when_typed_in():
    from app.player_profile import public_card

    rows = [_row(i) for i in range(4)]
    player = {"persona_name": "farm_or_die", "rank_tier": 54, "avatar_url": "https://x"}
    medal = build_profile(rows, player=player, mmr_raw=None, lang="uk", now=T0 + 5 * DAY)
    card = public_card(medal, "uk")
    assert card["name"] == "farm_or_die" and card["mmr"] is None  # a medal guess is not shown
    assert card["avatar"] is None  # not a Steam avatar address
    assert card["level"] == medal["level"]["level"] and card["stats"]["app_games"] == 4
    assert set(card) == {
        "lang",
        "name",
        "avatar",
        "title",
        "level",
        "rank_tier",
        "rank_label",
        "mmr",
        "mmr_change",
        "equipped",
        "achievements",
        "stats",
    }
    typed = build_profile(
        rows, player=player, mmr_raw=add_anchor(None, 3000, T0 - DAY), lang="uk", now=T0 + 5 * DAY
    )
    assert public_card(typed, "uk")["mmr"] == 3000 + 4 * MMR_STEP
    assert public_card(typed, "uk", show_mmr=False)["mmr"] is None
    worn = build_profile(
        rows,
        player=player,
        mmr_raw=None,
        cosmetics_raw='{"owned": ["title_farmer"], "equipped": {"title": "title_farmer"}}',
        lang="uk",
        now=T0,
    )
    assert public_card(worn, "uk")["title"] == "Фармило"


def test_the_public_card_keeps_only_the_steam_avatar_hash():
    from app.player_profile import avatar_hash

    image = "0123456789abcdef0123456789abcdef01234567"
    assert avatar_hash(f"https://avatars.steamstatic.com/{image}_full.jpg") == image
    assert avatar_hash(f"https://avatars.akamai.steamstatic.com/{image}_medium.jpg") == image
    assert (
        avatar_hash(
            f"https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/01/{image}_full.jpg"
        )
        == image
    )
    assert avatar_hash(f"https://evil.example/{image}_full.jpg") is None
    assert avatar_hash(f"http://avatars.steamstatic.com/{image}_full.jpg") is None
    assert avatar_hash(None) is None
