"""Compare with a friend: stats on OpenDota summaries, the service states and routes."""

from __future__ import annotations

from typing import Any

from match_fixtures import ME, FakeOpenDota, recent_matches

from app.friend_compare import compare, group_of
from app.opendota import OpenDotaError, summary_from_recent
from app.player_api import PLAYER_SERVICE

FRIEND = 900001  # a made-up account


def _rows(count: int, **overrides: Any) -> list[dict[str, Any]]:
    rows = []
    for raw in recent_matches(count, start_match_id=7_000_000):
        raw.update(overrides)
        rows.append(summary_from_recent(raw))
    return rows


class FriendFake(FakeOpenDota):
    """The linked player's matches, and the friend's (or none: a hidden profile)."""

    def __init__(self, friend_rows: list[dict[str, Any]] | None, *, fail: str | None = None):
        super().__init__(recent=recent_matches(12))
        self.friend_rows = friend_rows
        self.fail = fail

    def player(self, account_id: int) -> dict[str, Any]:
        if account_id != FRIEND:
            return super().player(account_id)
        if self.friend_rows is None:
            raise OpenDotaError("private", "no public profile")
        return {**super().player(account_id), "persona_name": "Friend", "rank_tier": 62}

    def recent_matches(self, account_id: int, *, limit: int = 30) -> list[dict[str, Any]]:
        if account_id != FRIEND:
            return super().recent_matches(account_id, limit=limit)
        if self.fail:
            raise OpenDotaError(self.fail, "down")
        self.calls.append(f"recent:{account_id}")
        return [dict(row) for row in (self.friend_rows or [])]


def _linked(client, tmp_path, fake):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=fake, auto_start=False)
    client.post("/player/link", json={"steam": str(ME)})
    PLAYER_SERVICE.jobs.run_pending(until=float("inf"))
    return PLAYER_SERVICE


def test_numbers_and_the_better_side():
    mine = _rows(10, gold_per_min=600, xp_per_min=700, deaths=4, radiant_win=True)
    theirs = _rows(10, gold_per_min=450, xp_per_min=690, deaths=8, radiant_win=False)
    result = compare(mine, theirs)
    rows = {row["key"]: row for row in result["rows"]}
    assert rows["gpm"] == {"key": "gpm", "me": 600, "friend": 450, "better": "me"}
    assert rows["deaths"]["better"] == "me"  # fewer deaths is better
    assert rows["xpm"]["better"] == "same"  # 700 vs 690: under 5 %
    assert rows["win_rate"]["me"] == 100 and rows["win_rate"]["friend"] == 0
    assert result["games"] == {"me": 10, "friend": 10} and result["enough"]
    common = result["common_heroes"]
    assert {h["hero"] for h in common} == {"Juggernaut", "Anti-Mage"}


def test_groups_by_farm_pace_and_too_few_games():
    cores = _rows(4, last_hits=300, duration=2400)
    supports = _rows(5, last_hits=40, duration=2400, start_time=1_700_000_000)
    assert group_of(cores[0]) == "core" and group_of(supports[0]) == "support"
    result = compare(cores + supports, cores[:2], "support")
    assert result["groups"]["support"] == {"me": 5, "friend": 0}
    assert result["games"]["friend"] == 0 and not result["enough"]
    assert all(row["better"] is None for row in result["rows"])
    # A game shorter than 10 minutes has no group.
    assert group_of({"last_hits": 10, "duration": 300}) is None


def test_friend_is_fetched_once_and_compared(client, tmp_path):
    fake = FriendFake(_rows(15))
    service = _linked(client, tmp_path, fake)
    answer = client.post("/player/friend?lang=en", json={"steam": str(FRIEND)}).json()
    assert answer["state"] == "loading" and answer["friend"]["account_id"] == FRIEND
    service.jobs.run_pending(until=float("inf"))
    ready = client.get("/player/friend?lang=en").json()
    assert ready["state"] == "ready"
    assert ready["friend"]["name"] == "Friend" and ready["friend"]["rank"] == "Ancient 2"
    assert ready["games"] == {"me": 12, "friend": 15}
    assert fake.calls.count(f"recent:{FRIEND}") == 1
    # Read again: from the cache, no new request.
    client.get("/player/friend?lang=en&group=core")
    service.jobs.run_pending(until=float("inf"))
    assert fake.calls.count(f"recent:{FRIEND}") == 1
    client.post("/player/friend/refresh?lang=en")
    service.jobs.run_pending(until=float("inf"))
    assert fake.calls.count(f"recent:{FRIEND}") == 2
    assert client.delete("/player/friend").json() == {"state": "none"}
    assert client.get("/player/friend").json() == {"state": "none"}


def test_hidden_profile_errors_and_bad_input(client, tmp_path):
    fake = FriendFake(None)  # hidden match data: no profile, no matches
    service = _linked(client, tmp_path, fake)
    client.post("/player/friend", json={"steam": str(FRIEND)})
    service.jobs.run_pending(until=float("inf"))
    assert client.get("/player/friend").json()["state"] == "private"

    fake.friend_rows, fake.fail = [], "timeout"
    client.post("/player/friend/refresh")
    service.store.cache_set(f"friend:matches:{FRIEND}", None)
    service.jobs.run_pending(until=float("inf"))
    answer = client.get("/player/friend").json()
    assert answer["state"] == "error" and answer["code"] == "timeout"

    assert client.post("/player/friend", json={"steam": str(ME)}).json() == {"state": "self"}
    bad = client.post("/player/friend", json={"steam": "steamcommunity.com/id/someone"})
    assert bad.status_code == 400 and bad.json()["code"] == "vanity_url"


def test_friend_needs_a_linked_account(client, tmp_path):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False)
    assert client.get("/player/friend").json() == {"state": "unlinked"}
