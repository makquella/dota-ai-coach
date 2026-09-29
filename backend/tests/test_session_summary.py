"""«Итог вечера»: the games of the latest sitting and the text to share."""

from __future__ import annotations

from app.focus_goal import new_focus
from app.session_summary import SESSION_CHAIN_GAP, SESSION_RECENT, session_summary, sitting

NOW = 2_000_000_000
HOUR = 3600


def _match(match_id, hours_ago, score, win, hero="Juggernaut", problems=(), deaths=4):
    return {
        "match_id": match_id,
        "hero": hero,
        "hero_id": {"Juggernaut": 8, "Lina": 25, "Axe": 2}[hero],
        "start_time": NOW - int(hours_ago * HOUR),
        "duration": 40 * 60,
        "score": score,
        "win": win,
        "deaths": deaths,
        "analysis": {
            "improvements": [{"id": p, "section": "survival", "params": {}} for p in problems],
            "problems": list(problems),
            "sections": {"survival": {}, "laning": {}},
        },
    }


def _usual(start_id, count=6, score=55):
    """Older matches, days before the sitting: the player's usual score."""
    return [_match(start_id + i, 48 + 24 * i, score, True) for i in range(count)]


def test_the_sitting_is_the_newest_chain_of_games():
    evening = [_match(3, 1.5, 70, True), _match(2, 2.5, 60, False), _match(1, 3.5, 50, True)]
    yesterday = [_match(0, 30, 90, True)]
    assert [m["match_id"] for m in sitting(evening + yesterday, NOW)] == [3, 2, 1]
    # A gap of more than SESSION_CHAIN_GAP between two starts ends the sitting.
    split = [_match(3, 1, 70, True), _match(2, 1 + SESSION_CHAIN_GAP / HOUR + 0.1, 60, True)]
    assert [m["match_id"] for m in sitting(split, NOW)] == [3]
    # A sitting that ended long ago is not «tonight».
    old = [
        _match(2, SESSION_RECENT / HOUR + 2, 60, True),
        _match(1, SESSION_RECENT / HOUR + 3, 60, True),
    ]
    assert sitting(old, NOW) == []


def test_the_evening_in_numbers_and_text_ru():
    matches = [
        _match(14, 1, 80, True, problems=["death_streak"], deaths=2),
        _match(
            13, 2, 50, False, hero="Lina", problems=["death_streak", "draft_better_pick"], deaths=9
        ),
        _match(12, 3, 65, True, deaths=4),
        *_usual(1),
    ]
    summary = session_summary(matches, NOW, "ru")
    assert (summary["games"], summary["wins"], summary["losses"]) == (3, 2, 1)
    assert (
        summary["avg_score"] == 65
        and summary["usual_score"] == 55
        and summary["score_change"] == 10
    )
    assert summary["minutes"] == 2 * 60 + 40
    assert summary["avg_deaths"] == 5.0
    assert summary["best"]["match_id"] == 14
    assert summary["heroes"] == [
        {"hero": "Juggernaut", "hero_id": 8, "games": 2, "wins": 2},
        {"hero": "Lina", "hero_id": 25, "games": 1, "wins": 0},
    ]
    assert summary["top_problem"]["id"] == "death_streak" and summary["top_problem"]["count"] == 2
    assert summary["id"] == f"{NOW - 3 * HOUR}:14"
    text = summary["text"].splitlines()
    assert text[0] == "Итог вечера в Dota 2 · Wardly"
    assert text[1] == "3 матча: 2 победы, 1 поражение · 2 ч 40 мин"
    assert text[2] == "Средняя оценка тренера: 65/100 (обычно 55)"
    assert text[3] == "Герои: Juggernaut 2–0, Lina 0–1"
    assert text[4] == "Лучший матч: Juggernaut, 80/100"
    assert text[5].startswith("Над чем работать: ") and text[5].endswith("(2 из 3)")
    assert text[-1] == "https://luhovyimvp.dev/?ref=session"
    # Nothing that names the player or the matches.
    assert "14" not in summary["text"].replace("2 из 3", "")


def test_the_text_in_english_without_a_usual_score():
    matches = [_match(2, 1, 70, True, hero="Axe"), _match(1, 2, None, False, hero="Axe")]
    summary = session_summary(matches, NOW, "en")
    assert summary["usual_score"] is None and "score_change" not in summary
    assert summary["avg_score"] == 70
    text = summary["text"].splitlines()
    assert text[1] == "2 matches: 1 win, 1 loss · 1 h 40 min"
    assert text[2] == "Average coach score: 70/100"
    assert text[3] == "Heroes: Axe 1–1"
    assert text[-1] == "https://luhovyimvp.dev/en/?ref=session"


def test_one_game_is_not_an_evening():
    assert session_summary([_match(1, 1, 70, True), *_usual(10)], NOW, "ru") is None
    assert session_summary([], NOW, "ru") is None


def test_the_id_changes_with_another_game():
    two = [_match(2, 2, 60, True), _match(1, 3, 60, True)]
    three = [_match(3, 1, 60, True), *two]
    assert session_summary(two, NOW, "en")["id"] != session_summary(three, NOW, "en")["id"]


def test_the_focus_counts_only_the_games_of_the_sitting():
    focus = new_focus("death_streak", "survival", {})
    focus["since_ts"] = NOW - 100 * HOUR
    matches = [
        _match(3, 1, 70, True),
        _match(2, 2, 60, True, problems=["death_streak"]),
        _match(1, 30, 60, True),  # yesterday: not in tonight's count
    ]
    summary = session_summary(matches, NOW, "ru", focus=focus)
    assert summary["focus"]["met"] == 1 and summary["focus"]["total"] == 2
    assert summary["focus"]["title"]
    assert "Фокус «" in summary["text"] and ": 1 из 2" in summary["text"]


def test_session_endpoint(client):
    assert client.get("/player/session?lang=ru").json() == {"session": None}
