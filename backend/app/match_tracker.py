"""
match_tracker.py - record the whole match of the local player from live GSI.

Dota sends GSI for the player at the keyboard, so the app can keep its own
timeline of every match it sees, with no replay parser and no internet:

- a sample every SAMPLE_EVERY_SECONDS of match clock (last hits, denies, gold,
  GPM/XPM, K/D/A, level, HP);
- deaths (clock, unspent gold, level, respawn time), buybacks;
- items, by the clock they first appeared in the inventory/stash;
- the hero's position in every sample and where each death happened (absolute
  map coordinates, see map_position());
- the last seconds before each death: HP, disables, saving items ready
  (last_moments.py, one entry per second, kept with the death as `last`).

A match is finished when Dota reports POST_GAME (win/loss known), when GSI
starts reporting another match id, or when no GSI arrived for STALE_AFTER
seconds (game closed / disconnected). The in-progress timeline is saved to
disk every few samples so a restart of the app does not lose it.

The finished timeline stays in the recovery journal until `on_finished`
(player_service.py) stores and reviews it successfully. Delivery is at least
once, with startup/status retries; the receiver must upsert idempotently.
Demo/replay states never reach this module.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.diagnostics import record_error
from app.dota_constants import hero_id_from_name, hero_name_from_npc
from app.gsi_state import normalize_abilities
from app.last_moments import LastSeconds
from app.live_tools import ready_abilities
from app.map_hints import observer_charges
from app.steam_ids import STEAM64_BASE

TIMELINE_VERSION = 1
RECOVERY_VERSION = 1
FINISH_RETRY_SECONDS = 5
SAMPLE_EVERY_SECONDS = 15
SAVE_EVERY_SAMPLES = 4
STALE_AFTER_SECONDS = 10 * 60
# Shorter games (abandoned in the first minutes) are not worth a review.
MIN_REVIEW_CLOCK_SECONDS = 5 * 60
MAX_ADVICE_NOTES = 80

POST_GAME_STATE = "DOTA_GAMERULES_STATE_POST_GAME"
_INVENTORY_PREFIXES = ("slot", "stash", "neutral", "teleport")


# Larger numbers (and inf/nan) are broken GSI, not game values: kept out of the
# timeline and SQLite (which stores 64-bit integers).
MAX_GSI_NUMBER = 10_000_000


def _int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if abs(number) <= MAX_GSI_NUMBER else None


def _id(value: Any) -> int | None:
    """Match, Steam and account ids: positive and within SQLite's 64-bit integers."""
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if 0 < number < 2**63 else None


def _inventory(items: dict[str, Any]) -> list[str] | None:
    """The item names in inventory slots 0-5, in slot order; None without an
    items block (a tick that did not send one)."""
    if not items:
        return None
    names = []
    for slot in range(6):
        name = _dict(items.get(f"slot{slot}")).get("name")
        if isinstance(name, str) and name.startswith("item_"):
            names.append(name)
    return names


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
    match_id = _id(map_block.get("matchid") or map_block.get("match_id"))
    return match_id if match_id and match_id > 0 else None


def account_from_gsi(player_block: dict[str, Any]) -> tuple[int | None, str | None]:
    """(account id, 64-bit steam id) of the player at the keyboard."""
    steam64 = _id(player_block.get("steamid"))
    account_id = _id(player_block.get("accountid"))
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
        self._delivery_lock = threading.Lock()
        self._current: dict[str, Any] | None = None
        self._pending: list[dict[str, Any]] = []
        self._retry_at = 0.0
        self._last_seen = 0.0
        self._unsaved_samples = 0
        # Not saved to disk: after a restart the next deaths fill it again.
        self._last_seconds = LastSeconds()
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
        with self._lock:
            if self._current and self._current["match_id"] != match_id:
                self._finish_locked(reason="next_match")
            # Opening the app on a score screen: nothing new to record, but
            # an earlier finish may still need delivery.
            if self._current is not None or map_block.get("game_state") != POST_GAME_STATE:
                if self._current is None:
                    self._current = self._new_match(match_id, player, payload)
                    self._last_seconds.reset()
                self._last_seen = self._clock()
                self._update_locked(payload, map_block, player)
                if map_block.get("game_state") == POST_GAME_STATE:
                    self.set_result(self._current, map_block.get("win_team"))
                    self._finish_locked(reason="post_game")
        self.retry_pending()

    def check_stale(self) -> None:
        """Finish a match whose GSI stopped (called from status polling)."""
        with self._lock:
            if self._current and self._clock() - self._last_seen > STALE_AFTER_SECONDS:
                self._finish_locked(reason="stale")
        self.retry_pending()

    def flush(self) -> None:
        """Save recovery state and retry pending finishes (app shutdown/backup)."""
        with self._lock:
            self._save_locked()
        self.retry_pending(force=True)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def retry_pending(self, *, force: bool = False) -> None:
        """Deliver durable finishes outside the state lock; ack only on success.

        Callback delivery is at least once, so the receiver must upsert by
        account/match. Concurrent GSI/status calls never deliver simultaneously.
        """
        if self.on_finished is None or not self._delivery_lock.acquire(blocking=False):
            return
        try:
            with self._lock:
                if not force and self._clock() < self._retry_at:
                    return
                pending = list(self._pending)
            for timeline in pending:
                with self._lock:
                    # Persist before handing anything to the receiver. A failed
                    # write keeps RAM and the previous checkpoint for recovery.
                    if not self._save_locked():
                        self._retry_at = self._clock() + FINISH_RETRY_SECONDS
                        return
                try:
                    self._emit(timeline)
                except Exception as error:  # noqa: BLE001 - retain until DB acknowledgement
                    record_error("match-finish", error)
                    with self._lock:
                        self._retry_at = self._clock() + FINISH_RETRY_SECONDS
                    return
                with self._lock:
                    self._pending.remove(timeline)
                    if not self._save_locked():
                        # The old journal still contains this entry. Replaying
                        # the idempotent callback is safe even after a restart.
                        self._pending.insert(0, timeline)
                        self._retry_at = self._clock() + FINISH_RETRY_SECONDS
                        return
                    self._retry_at = 0.0
        finally:
            self._delivery_lock.release()

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

    def last_death(self) -> dict[str, Any] | None:
        """The latest death of the match in progress: its clock and the rescue
        items that were ready and not pressed (last_moments `usable`)."""
        with self._lock:
            if not self._current or not self._current["deaths"]:
                return None
            death = self._current["deaths"][-1]
            last = death.get("last") or {}
            return {
                "match_id": self._current.get("match_id"),
                "t": death.get("t"),
                "usable": list(last.get("usable") or []),
                "burst_s": last.get("burst_s"),
                "team": self._current.get("team"),
                # Every death of the match so far with its position (repeated places).
                "places": [
                    {"t": d.get("t"), "x": d.get("x"), "y": d.get("y")}
                    for d in self._current["deaths"]
                ],
            }

    def advice_count(self, decision_points: set[str]) -> int:
        """Advice of these decision points already given in the match in progress."""
        with self._lock:
            if not self._current:
                return 0
            return sum(
                1 for a in self._current.get("advice") or [] if a.get("dp") in decision_points
            )

    def death_moments(self) -> list[dict[str, Any]]:
        """Every death of the match in progress with its last seconds (for the
        situational item: situational_items.py)."""
        with self._lock:
            if not self._current:
                return []
            return [{"t": d.get("t"), "last": d.get("last")} for d in self._current["deaths"]]

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
        # Game time from the start of the replay minus the match clock: turns a
        # match moment into a replay tick («watch this moment» in the review).
        game_time = _int(map_block.get("game_time"))
        if game_time is not None and game_time >= clock and "clock_offset" not in current:
            current["clock_offset"] = game_time - clock
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
        # The hero's own escape / defensive abilities ready now (live_tools.py).
        ready = ready_abilities(hero.get("name"), normalize_abilities(payload.get("abilities")))
        self._last_seconds.observe(clock, hero, _dict(payload.get("items")), ready)
        self._track_deaths(current, snapshot, hero, last)
        self._track_buyback(current, clock, hero, last)
        self._track_items(current, clock, _dict(payload.get("items")))
        self._track_wards(current, _dict(payload.get("items")), snapshot["alive"])

        samples = current["samples"]
        if not samples or clock - samples[-1]["t"] >= SAMPLE_EVERY_SECONDS:
            samples.append({key: value for key, value in snapshot.items() if value is not None})
            self._unsaved_samples += 1
            if self._unsaved_samples >= SAVE_EVERY_SAMPLES:
                self._save_locked()
        inventory = _inventory(_dict(payload.get("items")))
        current["final"] = {
            # The six inventory slots at the last tick (item_* names; the match
            # table's icons). An items block missing from a tick keeps the last one.
            "inventory": inventory
            if inventory is not None
            else (current.get("final") or {}).get("inventory", []),
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
            moments = self._last_seconds.summarize(snapshot["t"])
            if moments:
                current["deaths"][-1]["last"] = moments
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

    def _track_wards(self, current: dict[str, Any], items: dict[str, Any], alive: Any) -> None:
        """Observer wards placed: the carried count going down while alive (a ward
        dropped for an ally counts too). Kept only once an items block was seen,
        so a match without one says nothing about vision."""
        charges = observer_charges(items)
        if charges is None:
            return
        previous = current.get("_ward_charges")
        current["_ward_charges"] = charges
        current.setdefault("obs_placed", 0)
        if previous is not None and charges < previous and alive is not False:
            current["obs_placed"] += previous - charges

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

    def _finish_locked(self, *, reason: str) -> None:
        current = self._current
        if not current:
            return
        if reason == "post_game":
            current["finished"] = True
        current["end_reason"] = reason
        current["ended_at"] = datetime.now(UTC).isoformat()
        current["duration"] = current.get("last_clock")
        if (current.get("last_clock") or 0) >= MIN_REVIEW_CLOCK_SECONDS and current.get("hero"):
            self._pending.append(current)
        self._current = None
        self._save_locked()

    def set_result(self, timeline: dict[str, Any], win_team: str | None) -> None:
        team = str(timeline.get("team") or "").lower()
        if win_team and team in {"radiant", "dire"}:
            timeline["win"] = str(win_team).lower() == team

    def _emit(self, timeline: dict[str, Any]) -> None:
        public = {key: value for key, value in timeline.items() if not key.startswith("_")}
        if self.on_finished is not None:
            self.on_finished(public)

    # --- persistence ----------------------------------------------------------

    def _save_locked(self) -> bool:
        try:
            if self._current is None and not self._pending:
                self.state_path.unlink(missing_ok=True)
                self._unsaved_samples = 0
                return True
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            recovery = {
                "recovery_version": RECOVERY_VERSION,
                "current": self._current,
                "pending": self._pending,
            }
            with tmp.open("w", encoding="utf-8") as stream:
                json.dump(recovery, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            tmp.replace(self.state_path)
            self._unsaved_samples = 0
            return True
        except OSError as error:
            record_error("match-recovery", error)
            return False

    def _load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        if data.get("recovery_version") == RECOVERY_VERSION:
            current = data.get("current")
            if isinstance(current, dict) and current.get("version") == TIMELINE_VERSION:
                self._current = current
            pending = data.get("pending")
            if isinstance(pending, list):
                self._pending = [
                    timeline
                    for timeline in pending
                    if isinstance(timeline, dict) and timeline.get("version") == TIMELINE_VERSION
                ]
        elif data.get("version") == TIMELINE_VERSION:
            # Legacy in-progress files from 0.53.3 and earlier.
            self._current = data
        if self._current is not None:
            self._last_seen = self._clock()
