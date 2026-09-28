"""Advice counts for the opt-in anonymous statistics (app/usage_stats.py)."""

from __future__ import annotations

from app.usage_stats import usage_stats

DAY = 86400
SINCE = 1_800_000_000


def _match(start, advice=(), ignored=()):
    return {
        "match_id": 99,
        "hero": "Juggernaut",
        "start_time": start,
        "analysis": {
            "advice": [
                {"t": t, "dp": dp, "mode": mode, "action": "text"} for t, dp, mode in advice
            ],
            "advice_follow": {
                "urgent": 1,
                "ignored": [{"t": t, "death_t": t + 10} for t in ignored],
            },
        },
    }


def test_counts_advice_and_ignored_warnings_of_the_period_only():
    matches = [
        _match(
            SINCE + 100,
            advice=[
                (300, "LOW_HP_WARNING", "urgent"),
                (500, "LANING_FARM_CHECK", "coaching"),
                (700, "LOW_HP_WARNING", "urgent"),
                (900, "bad kind!", "coaching"),
            ],
            ignored=[700],
        ),
        _match(SINCE + 200),  # analysed, no live advice (an OpenDota-only match)
        _match(SINCE + DAY + 5, advice=[(100, "LOW_HP_WARNING", "urgent")]),  # the next day
        {"start_time": SINCE + 300, "analysis": None},  # not analysed
    ]
    usage = usage_stats(matches, SINCE, SINCE + DAY)
    assert usage == {
        "matches": 2,
        "with_advice": 1,
        "advice": {"LOW_HP_WARNING": 2, "LANING_FARM_CHECK": 1},
        "ignored": {"LOW_HP_WARNING": 1},
    }
    # Nothing that names the match, the hero or the texts.
    assert "99" not in str(usage) and "Juggernaut" not in str(usage) and "text" not in str(usage)


def test_the_usage_endpoint(client):
    body = client.get(f"/player/usage?since={SINCE}&until={SINCE + DAY}").json()
    assert body["usage"] == {"matches": 0, "with_advice": 0, "advice": {}, "ignored": {}}
    assert client.get(f"/player/usage?since={SINCE}&until={SINCE - 1}").status_code == 422
    assert client.get(f"/player/usage?since={SINCE}&until={SINCE + 9 * DAY}").status_code == 422
