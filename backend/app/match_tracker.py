"""
match_tracker.py - record the whole match of the local player from live GSI.

Dota sends GSI for the player at the keyboard, so the app can keep its own
timeline of every match it sees, with no replay parser and no internet:

- a sample every SAMPLE_EVERY_SECONDS of match clock (last hits, denies, gold,
  GPM/XPM, K/D/A, level, HP);
- deaths (clock, unspent gold, level, respawn time), buybacks;
- items, by the clock they first appeared in the inventory/stash;
- the hero's position in every sample and where each death happened (absolute
  map coordinates, see map_position()).

A match is finished when Dota reports POST_GAME (win/loss known), when GSI
starts reporting another match id, or when no GSI arrived for STALE_AFTER
seconds (game closed / disconnected). The in-progress timeline is saved to
disk every few samples so a restart of the app does not lose it.

The finished timeline goes to `on_finished` (player_service.py stores and
reviews it). Demo/replay states never reach this module.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.dota_constants import hero_id_from_name, hero_name_from_npc
from app.steam_ids import STEAM64_BASE

TIMELINE_VERSION = 1
SAMPLE_EVERY_SECONDS = 15
SAVE_EVERY_SAMPLES = 4
STALE_AFTER_SECONDS = 10 * 60
# Shorter games (abandoned in the first minutes) are not worth a review.
MIN_REVIEW_CLOCK_SECONDS = 5 * 60
MAX_ADVICE_NOTES = 80

POST_GAME_STATE = "DOTA_GAMERULES_STATE_POST_GAME"
_INVENTORY_PREFIXES = ("slot", "stash", "neutral", "teleport")


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


# GSI gives world coordinates (map centre 0); the timeline keeps the absolute
# ones used by replays and advice_context.py (centre 16384), rounded to units.
MAP_CENTER = 16384


def map_position(hero: dict[str, Any]) -> tuple[int, int] | None:
    try:
        x, y = float(hero["xpos"]), float(hero["ypos"])
    except (KeyError, TypeError, ValueError):
        return None
    return round(x) + MAP_CENTER, round(y) + MAP_CENTER


def is_spectator_payload(payload: dict[str, Any]) -> bool:
    """Watching a replay or a live game in the client: GSI then sends every
    player and hero per team ("team2"/"team3") instead of the local player."""
    return any(
        key in _dict(payload.get(block))
        for block in ("player", "hero")
        for key in ("team2", "team3")
    )


def match_id_from_gsi(map_block: dict[str, Any]) -> int | None:
    match_id = _int(map_block.get("matchid") or map_block.get("match_id"))
    return match_id if match_id and match_id > 0 else None


def account_from_gsi(player_block: dict[str, Any]) -> tuple[int | None, str | None]:
    """(account id, 64-bit steam id) of the player at the keyboard."""
    steam64 = _int(player_block.get("steamid"))
    account_id = _int(player_block.get("accountid"))
    if steam64 and steam64 > STEAM64_BASE:
        return (account_id or steam64 - STEAM64_BASE), str(steam64)
    if account_id and account_id > 0:
        return account_id, str(account_id + STEAM64_BASE)
    return None, None


class MatchTracker:
    def __init__(
        self,
        state_path: Path,
        *,
        on_finished: Callable[[dict[str, Any]], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.state_path = Path(state_path)
        self.on_finished = on_finished
        self._clock = clock
        self._lock = threading.Lock()
        self._current: dict[str, Any] | None = None
        self._last_seen = 0.0
        self._unsaved_samples = 0
        self._load()

    # --- public ---------------------------------------------------------------

    def observe(self, payload: dict[str, Any]) -> None:
        """Feed one raw GSI payload (called from POST /gsi)."""
        if is_spectator_payload(payload):
            # Someone else's game: never the player's history.
            return
        map_block = _dict(payload.get("map"))
        player = _dict(payload.get("player"))
        match_id = match_id_from_gsi(map_block)
        if match_id is None:
            return
        finished: dict[str, Any] | None = None
        with self._lock:
            if self._current and self._current["match_id"] != match_id:
                finished = self._finish_locked(reason="next_match")
            if self._current is None:
                if map_block.get("game_state") == POST_GAME_STATE:
                    # Opening the app on a score screen: nothing to record.
                    return
                self._current = self._new_match(match_id, player, payload)
            self._last_seen = self._clock()
            self._update_locked(payload, map_block, player)
            if map_block.get("game_state") == POST_GAME_STATE and finished is None:
                self.set_result(self._current, map_block.get("win_team"))
                finished = self._finish_locked(reason="post_game")
        if finished is not None:
            self._emit(finished)

    def check_stale(self) -> None:
        """Finish a match whose GSI stopped (called from status polling)."""
        finished = None
        with self._lock:
            if self._current and self._clock() - self._last_seen > STALE_AFTER_SECONDS:
                finished = self._finish_locked(reason="stale")
        if finished is not None:
            self._emit(finished)

    def flush(self) -> None:
        """Save the in-progress match (app shutdown)."""
        with self._lock:
            self._save_locked()

    def current(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._current:
                return None
            return {
                "match_id": self._current["match_id"],
                "account_id": self._current.get("account_id"),
                "hero": self._current.get("hero"),
                "clock": self._current.get("last_clock"),
                "samples": len(self._current["samples"]),
            }

    def note_advice(
        self, clock: Any, decision_point: str, action: str, reason: str, mode: str
    ) -> None:
        """Remember a piece of live advice for the post-match review (capped)."""
        clock = _int(clock)
        with self._lock:
            current = self._current
            if current is None or clock is None or clock < 0 or not action:
                return
            advice = current.setdefault("advice", [])
            if len(advice) >= MAX_ADVICE_NOTES:
                return
            advice.append(
                {
                    "t": clock,
                    "dp": decision_point,
                    "action": action[:200],
                    "reason": (reason or "")[:300],
                    "mode": mode,
                }
            )

    # --- recording ------------------------------------------------------------

    def _new_match(
        self, match_id: int, player: dict[str, Any], payload: dict[str, Any]
    ) -> dict[str, Any]:
        account_id, steam64 = account_from_gsi(player)
        return {
            "version": TIMELINE_VERSION,
            "match_id": match_id,
            "account_id": account_id,
            "steam_id64": steam64,
            "player_name": player.get("name"),
            "team": player.get("team_name"),
            "hero": None,
            "hero_id": None,
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": None,
            "finished": False,
            "end_reason": None,
            "win": None,
            "duration": None,
            "last_clock": None,
            "samples": [],
            "deaths": [],
            "buybacks": [],
            "items": [],
            # Live advice shown during the match (English, as the pipeline wrote it).
            "advice": [],
            "final": {},
            "scores": {},
            "_last": {},
            "_items_seen": [],
        }

    def _update_locked(
        self, payload: dict[str, Any], map_block: dict[str, Any], player: dict[str, Any]
    ) -> None:
        current = self._current
        assert current is not None
        hero = _dict(payload.get("hero"))
        clock = _int(map_block.get("clock_time"))
        if current.get("account_id") is None:
            account_id, steam64 = account_from_gsi(player)
            current["account_id"], current["steam_id64"] = account_id, steam64
        current["player_name"] = player.get("name") or current.get("player_name")
        current["team"] = player.get("team_name") or current.get("team")
        hero_npc = hero.get("name")
        if hero_npc and hero_npc != current.get("hero_npc"):
            current["hero_npc"] = hero_npc
            current["hero"] = hero_name_from_npc(hero_npc)
            current["hero_id"] = hero_id_from_name(hero_npc)
        if clock is None or clock < 0:
            return
        current["last_clock"] = clock
        # Team kill totals, for kill participation without OpenDota.
        for team in ("radiant", "dire"):
            score = _int(map_block.get(f"{team}_score"))
            if score is not None:
                current["scores"][team] = score

        snapshot = {
            "t": clock,
            "lh": _int(player.get("last_hits")),
            "dn": _int(player.get("denies")),
            "gold": _int(player.get("gold")),
            "gpm": _int(player.get("gpm")),
            "xpm": _int(player.get("xpm")),
            "k": _int(player.get("kills")),
            "d": _int(player.get("deaths")),
            "a": _int(player.get("assists")),
            "lvl": _int(hero.get("level")),
            "hp": _int(hero.get("health_percent")),
            "alive": hero.get("alive") if isinstance(hero.get("alive"), bool) else None,
        }
        position = map_position(hero)
        if position is not None and snapshot["alive"] is not False:
            snapshot["x"], snapshot["y"] = position
        last = current["_last"]
        self._track_deaths(current, snapshot, hero, last)
        self._track_buyback(current, clock, hero, last)
        self._track_items(current, clock, _dict(payload.get("items")))

        samples = current["samples"]
        if not samples or clock - samples[-1]["t"] >= SAMPLE_EVERY_SECONDS:
            samples.append({key: value for key, value in snapshot.items() if value is not None})
            self._unsaved_samples += 1
            if self._unsaved_samples >= SAVE_EVERY_SAMPLES:
                self._save_locked()
        current["final"] = {
            "kills": snapshot["k"],
            "deaths": snapshot["d"],
            "assists": snapshot["a"],
            "last_hits": snapshot["lh"],
            "denies": snapshot["dn"],
            "gpm": snapshot["gpm"],
            "xpm": snapshot["xpm"],
            "level": snapshot["lvl"],
        }
        current["_last"] = {
            "deaths": snapshot["d"],
            "buyback_cooldown": _int(hero.get("buyback_cooldown")),
            "alive": snapshot["alive"],
            # Where the hero last stood alive: the death position.
            "x": snapshot.get("x", last.get("x")),
            "y": snapshot.get("y", last.get("y")),
        }

    def _track_deaths(
        self,
        current: dict[str, Any],
        snapshot: dict[str, Any],
        hero: dict[str, Any],
        last: dict[str, Any],
    ) -> None:
        deaths = snapshot["d"]
        previous = last.get("deaths")
        if deaths is not None and previous is not None and deaths > previous:
            current["deaths"].append(
                {
                    "t": snapshot["t"],
                    "gold": snapshot["gold"],
                    "level": snapshot["lvl"],
                    "respawn": _int(hero.get("respawn_seconds")),
                    "buyback_ready": _int(hero.get("buyback_cooldown")) == 0,
                    "x": last.get("x"),
                    "y": last.get("y"),
                }
            )
            self._save_locked()
        elif current["deaths"] and snapshot["alive"] is False:
            # respawn_seconds is sometimes only filled a tick after the death.
            respawn = _int(hero.get("respawn_seconds"))
            last_death = current["deaths"][-1]
            if respawn and respawn > (last_death.get("respawn") or 0):
                last_death["respawn"] = respawn

    def _track_buyback(
        self, current: dict[str, Any], clock: int, hero: dict[str, Any], last: dict[str, Any]
    ) -> None:
        cooldown = _int(hero.get("buyback_cooldown"))
        previous = last.get("buyback_cooldown")
        if cooldown and (previous == 0) and last.get("alive") is False:
            current["buybacks"].append({"t": clock})

    def _track_items(self, current: dict[str, Any], clock: int, items: dict[str, Any]) -> None:
        seen = current["_items_seen"]
        for slot, value in items.items():
            if not str(slot).startswith(_INVENTORY_PREFIXES):
                continue
            name = _dict(value).get("name")
            if not name or name == "empty" or name in seen:
                continue
            seen.append(name)
            current["items"].append({"t": clock, "item": name})

    # --- finishing ------------------------------------------------------------

    def _finish_locked(self, *, reason: str) -> dict[str, Any] | None:
        current = self._current
        self._current = None
        self._unsaved_samples = 0
        self._delete_saved_locked()
        if not current:
            return None
        if reason == "post_game":
            current["finished"] = True
        current["end_reason"] = reason
        current["ended_at"] = datetime.now(UTC).isoformat()
        current["duration"] = current.get("last_clock")
        if (current.get("last_clock") or 0) < MIN_REVIEW_CLOCK_SECONDS:
            return None
        if not current.get("hero"):
            # No hero ever seen (not the player's own game): nothing to review.
            return None
        return current

    def set_result(self, timeline: dict[str, Any], win_team: str | None) -> None:
        team = str(timeline.get("team") or "").lower()
        if win_team and team in {"radiant", "dire"}:
            timeline["win"] = str(win_team).lower() == team

    def _emit(self, timeline: dict[str, Any]) -> None:
        public = {key: value for key, value in timeline.items() if not key.startswith("_")}
        if self.on_finished is not None:
            self.on_finished(public)

    # --- persistence ----------------------------------------------------------

    def _save_locked(self) -> None:
        self._unsaved_samples = 0
        if not self._current:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._current, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.state_path)
        except OSError:
            # Losing the in-progress file only matters if the app restarts mid-game.
            pass

    def _delete_saved_locked(self) -> None:
        with contextlib.suppress(OSError):
            self.state_path.unlink(missing_ok=True)

    def _load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict) and data.get("version") == TIMELINE_VERSION:
            self._current = data
            self._last_seen = self._clock()
