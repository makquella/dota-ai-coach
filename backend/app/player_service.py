"""
player_service.py - the linked player, their match history and reviews.

Ties together the SQLite store, the live match tracker, the OpenDota client
and the analyses:

- Account: the Steam account playing is read from GSI (player.steamid) and
  linked automatically the first time; it can also be linked by hand (Steam
  ID, Friend ID or profile link). A different account seen in GSI later is
  offered as "detected", never switched silently.
- History: a background sync pulls the profile and the last matches from
  OpenDota and reviews the most recent ones.
- After a live match: the GSI timeline is stored and reviewed at once
  (offline), then OpenDota is asked to parse the replay; when the parsed
  match arrives the review is rebuilt with the full data.

Network work runs on one background thread (JobQueue), never on the GSI path.
Without internet (or with OPENDOTA_ENABLED=false) everything still works from
the app's own GSI recordings.

AI coach (optional, coach_review.py): with a Groq / OpenRouter key the rule
based reviews get a coach's explanation on a second job thread; results are
cached per match, language and facts, and rebuilt when the facts change.
"""

from __future__ import annotations

import contextlib
import heapq
import itertools
import json
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.analysis_texts import render_analysis
from app.career_analysis import analyze_career
from app.coach_llm import PROVIDERS, AISettings, CoachLLM, CoachLLMError, settings_from
from app.coach_review import (
    career_facts,
    facts_hash,
    match_facts,
    recent_match_line,
    review_career,
    review_match,
)
from app.dota_constants import REVIEWABLE_LOBBY_TYPES
from app.match_facts import facts_from_opendota, facts_from_timeline, merge_facts
from app.match_tracker import MatchTracker, account_from_gsi
from app.opendota import (
    OpenDotaClient,
    OpenDotaError,
    my_player,
    summary_from_match,
    trim_match,
)
from app.player_store import PlayerStore
from app.post_match_analysis import analyze_match
from app.steam_ids import parse_account_id, steam64_from_account_id

RECENT_MATCHES_LIMIT = 50
REVIEW_RECENT_MATCHES = 12
# OpenDota learns about a match a minute or two after it ends.
FIRST_FETCH_DELAY_SECONDS = 120
PARSE_POLL_SECONDS = 90
PARSE_POLL_ATTEMPTS = 12
# OpenDota meta data cache (player_store cache table).
ITEM_CONSTANTS_KEY = "opendota:items"
POPULARITY_KEY = "opendota:item_popularity"
TIMINGS_KEY = "opendota:item_timings"
HERO_STATS_KEY = "opendota:hero_stats"
META_TTL_SECONDS = 7 * 24 * 3600
HERO_STATS_TTL_SECONDS = 24 * 3600
# AI coach.
AI_SETTINGS_KEY = "ai_settings"
# The replay is still being parsed: wait for the full data before asking the model.
COACH_WAITS_FOR = {"waiting_opendota", "parsing"}
COACH_MIN_CAREER_MATCHES = 3
# "Overloaded" (HTTP 503 on every model) costs no quota: retry by itself later.
COACH_BUSY_RETRY_SECONDS = (60, 120, 180)


class JobQueue:
    """Delayed, de-duplicated jobs on one daemon thread (or run by hand in tests)."""

    def __init__(
        self,
        *,
        auto_start: bool = True,
        clock: Callable[[], float] = time.monotonic,
        name: str = "player-jobs",
    ) -> None:
        self.auto_start = auto_start
        self.name = name
        self._clock = clock
        self._heap: list[tuple[float, int, str]] = []
        self._jobs: dict[str, Callable[[], None]] = {}
        self._counter = itertools.count()
        self._cond = threading.Condition()
        self._thread: threading.Thread | None = None
        self._stopped = False

    def submit(self, key: str, fn: Callable[[], None], *, delay: float = 0.0) -> None:
        with self._cond:
            if key in self._jobs:
                return
            self._jobs[key] = fn
            heapq.heappush(self._heap, (self._clock() + delay, next(self._counter), key))
            self._cond.notify()
        if self.auto_start:
            self._ensure_thread()

    def pending(self) -> list[str]:
        with self._cond:
            return list(self._jobs)

    def run_pending(self, *, until: float | None = None) -> int:
        """Run every job due by `until` (default: now). Returns how many ran."""
        ran = 0
        while True:
            with self._cond:
                limit = self._clock() if until is None else until
                if not self._heap or self._heap[0][0] > limit:
                    return ran
                _, _, key = heapq.heappop(self._heap)
                fn = self._jobs.pop(key, None)
            if fn is not None:
                fn()
                ran += 1

    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify_all()

    def _ensure_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name=self.name, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            with self._cond:
                if self._stopped:
                    return
                wait = None
                if self._heap:
                    wait = max(0.0, self._heap[0][0] - self._clock())
                if wait is None or wait > 0:
                    self._cond.wait(timeout=wait if wait is not None else 60)
                    continue
            # A failing job must not kill the worker.
            with contextlib.suppress(Exception):
                self.run_pending()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class PlayerService:
    def __init__(
        self,
        data_dir: Path,
        *,
        client: OpenDotaClient | None = None,
        auto_start: bool = True,
        llm: Any = None,
        env_ai: AISettings | None = None,
    ) -> None:
        self.configure(data_dir, client=client, auto_start=auto_start, llm=llm, env_ai=env_ai)

    def configure(
        self,
        data_dir: Path,
        *,
        client: OpenDotaClient | None = None,
        auto_start: bool = True,
        llm: Any = None,
        env_ai: AISettings | None = None,
    ) -> None:
        """(Re)open the store in `data_dir`; used at startup and by tests.

        `llm` replaces the configured AI client (tests); `env_ai` is the key
        from .env used when the player has not entered one.
        """
        for name in ("jobs", "ai_jobs"):
            old_jobs = getattr(self, name, None)
            if old_jobs is not None:
                old_jobs.stop()
        old_store = getattr(self, "store", None)
        if old_store is not None:
            old_store.close()
        self.data_dir = Path(data_dir)
        self.client = client
        self.store = PlayerStore(self.data_dir / "coach.sqlite3")
        self.jobs = JobQueue(auto_start=auto_start)
        # Model calls take up to a couple of minutes: their own thread, so they
        # never hold back OpenDota syncs.
        self.ai_jobs = JobQueue(auto_start=auto_start, name="coach-ai")
        self.llm = llm
        self.env_ai = env_ai
        self._coach_lock = threading.Lock()
        self._coach_jobs: dict[str, dict[str, Any]] = {}
        self.tracker = MatchTracker(
            self.data_dir / "live_match.json", on_finished=self._on_match_finished
        )
        self._detected: dict[str, Any] | None = None
        self._sync: dict[str, Any] = {
            "state": "idle",
            "at": None,
            "error": None,
            "error_code": None,
        }

    def shutdown(self) -> None:
        self.tracker.flush()
        self.jobs.stop()
        self.ai_jobs.stop()

    # --- GSI ------------------------------------------------------------------

    def observe_gsi(self, payload: dict[str, Any]) -> None:
        player: dict[str, Any] = (
            payload["player"] if isinstance(payload.get("player"), dict) else {}
        )
        account_id, steam64 = account_from_gsi(player)
        if account_id:
            self._note_detected(account_id, steam64, player.get("name"))
        self.tracker.observe(payload)

    def _note_detected(self, account_id: int, steam64: str | None, name: Any) -> None:
        if self._detected and self._detected["account_id"] == account_id:
            return
        self._detected = {"account_id": account_id, "steam_id64": steam64, "persona_name": name}
        self.store.upsert_player(account_id, source="gsi", steam_id64=steam64, persona_name=name)
        if self.store.primary_account_id() is None:
            self.store.set_primary(account_id, source="gsi")
            self.request_sync()

    def check_stale(self) -> None:
        self.tracker.check_stale()

    # --- account --------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        primary = self.store.primary_account_id()
        player = self.store.get_player(primary) if primary else None
        detected = self._detected
        return {
            "linked": primary is not None,
            "account_id": primary,
            "source": self.store.primary_source(),
            "player": _public_player(player, primary),
            "detected": detected if detected and detected["account_id"] != primary else None,
            "opendota": self.client is not None,
            "sync": dict(self._sync),
            "matches": self.store.count_matches(primary) if primary else 0,
            "live_match": self.tracker.current(),
            "last_review": self._last_review(),
            "pending_jobs": len(self.jobs.pending()),
            "ai": {"configured": self.ai_configured()},
        }

    def link(self, value: Any) -> dict[str, Any]:
        account_id = parse_account_id(value)
        self.store.upsert_player(
            account_id, source="manual", steam_id64=str(steam64_from_account_id(account_id))
        )
        self.store.set_primary(account_id, source="manual")
        self.request_sync()
        return self.status()

    def unlink(self) -> dict[str, Any]:
        self.store.clear_primary()
        return self.status()

    # --- history --------------------------------------------------------------

    def list_matches(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        primary = self.store.primary_account_id()
        if primary is None:
            return {"linked": False, "items": [], "total": 0}
        return {
            "linked": True,
            "items": self.store.list_matches(primary, limit=limit, offset=offset),
            "total": self.store.count_matches(primary),
            "sync": dict(self._sync),
        }

    def match_detail(
        self, match_id: int, lang: str, *, force_coach: bool = False
    ) -> dict[str, Any] | None:
        primary = self.store.primary_account_id()
        if primary is None:
            return None
        record = self.store.get_match(primary, match_id)
        if record is None:
            return None
        analysis = record.get("analysis")
        if analysis is None and (record.get("opendota") or record.get("timeline")):
            analysis = self._rebuild_analysis(primary, match_id)
        if analysis is None and self.client is not None:
            self.fetch_match(match_id, request_parse=False)
        detail = {
            "match_id": match_id,
            "summary": {key: record.get(key) for key in _SUMMARY_KEYS},
            "sources": record.get("sources"),
            "parse_status": record.get("parse_status") or "",
            "analysis": render_analysis(analysis, lang) if analysis else None,
            "scoreboard": _scoreboard(record.get("opendota")),
            "loading": analysis is None and self.client is not None,
        }
        detail["coach"] = self._match_coach(primary, match_id, detail, lang, force=force_coach)
        return detail

    def career(self, lang: str, *, force_coach: bool = False) -> dict[str, Any]:
        primary = self.store.primary_account_id()
        if primary is None:
            return {"linked": False}
        player = self.store.get_player(primary) or {}
        matches = self.store.matches_for_career(primary, limit=RECENT_MATCHES_LIMIT)
        result = analyze_career(
            matches,
            lang,
            rank_tier=player.get("rank_tier"),
            hero_stats=self.store.cache_get(HERO_STATS_KEY),
        )
        result["linked"] = True
        recent = [
            recent_match_line(render_analysis(m["analysis"], lang))
            for m in matches
            if m.get("analysis")
        ]
        result["coach"] = self._career_coach(primary, result, recent, lang, force=force_coach)
        return result

    # --- AI coach ----------------------------------------------------------------

    def ai_settings(self) -> AISettings | None:
        raw = self.store.get_meta(AI_SETTINGS_KEY)
        stored = None
        if raw:
            with contextlib.suppress(ValueError):
                stored = settings_from(json.loads(raw), source="app")
        return stored or self.env_ai

    def ai_status(self) -> dict[str, Any]:
        settings = self.ai_settings()
        base = settings.public() if settings else {"configured": self.llm is not None}
        return {
            **base,
            "providers": [
                {"id": key, "label": value["label"], "model": value["model"]}
                for key, value in PROVIDERS.items()
            ],
        }

    def set_ai(self, provider: str, api_key: str, model: str | None = None) -> dict[str, Any]:
        settings = settings_from(
            {"provider": provider, "api_key": api_key, "model": model}, source="app"
        )
        if settings is None:
            raise ValueError("bad_ai_settings")
        self.store.set_meta(
            AI_SETTINGS_KEY,
            json.dumps(
                {"provider": settings.provider, "api_key": settings.api_key, "model": model}
            ),
        )
        with self._coach_lock:
            # A new key may fix earlier errors (bad key, rate limit).
            self._coach_jobs = {k: v for k, v in self._coach_jobs.items() if v["state"] != "error"}
        return self.ai_status()

    def clear_ai(self) -> dict[str, Any]:
        self.store.set_meta(AI_SETTINGS_KEY, None)
        return self.ai_status()

    def check_ai(self) -> dict[str, Any]:
        """One small request with the current settings (runs in the request thread)."""
        client = self._coach_client(check=True)
        if client is None:
            return {"ok": False, "code": "no_key"}
        try:
            client.check()
        except CoachLLMError as error:
            return {"ok": False, "code": error.code}
        return {"ok": True}

    def ai_configured(self) -> bool:
        return self.llm is not None or self.ai_settings() is not None

    def _coach_client(self, *, check: bool = False) -> Any:
        if self.llm is not None:
            return self.llm
        settings = self.ai_settings()
        if settings is None:
            return None
        return CoachLLM(settings, timeout=30.0) if check else CoachLLM(settings)

    def _known_items(self) -> list[str]:
        constants = self.store.cache_get(ITEM_CONSTANTS_KEY) or {}
        return [str(info.get("name")) for info in (constants.get("items") or {}).values()]

    def _match_coach(
        self,
        account_id: int,
        match_id: int,
        detail: dict[str, Any],
        lang: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        facts = match_facts(detail)
        if facts is None:
            return {"state": "none"}
        waiting = detail.get("parse_status") in COACH_WAITS_FOR
        return self._coach_state(
            f"coach:match:{account_id}:{match_id}:{lang}",
            facts,
            lang,
            kind="match",
            force=force,
            hold="waiting" if waiting and not force else None,
        )

    def _career_coach(
        self,
        account_id: int,
        career: dict[str, Any],
        recent: list[dict[str, Any]],
        lang: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        facts = career_facts(career, recent)
        if facts is None or len(recent) < COACH_MIN_CAREER_MATCHES:
            return {"state": "not_enough", "need": COACH_MIN_CAREER_MATCHES}
        return self._coach_state(
            f"coach:career:{account_id}:{lang}", facts, lang, kind="career", force=force
        )

    def _coach_state(
        self,
        key: str,
        facts: dict[str, Any],
        lang: str,
        *,
        kind: str,
        force: bool,
        hold: str | None = None,
    ) -> dict[str, Any]:
        """Cached review, or queue a new one: off / waiting / pending / ready / error."""
        digest = facts_hash(facts, lang)
        cached = self.store.cache_get(key)
        shown = _coach_public(cached, stale=bool(cached) and cached.get("hash") != digest)
        if not self.ai_configured():
            return {"state": "off", **shown}
        if cached and cached.get("hash") == digest and not force:
            return {"state": "ready", **shown}
        with self._coach_lock:
            job = self._coach_jobs.get(key)
            if job and job["hash"] == digest:
                if job["state"] == "pending":
                    return {"state": "pending", **shown}
                if job["state"] == "error" and not force:
                    return {"state": "error", "error": job["error"], **shown}
            if hold:
                return {"state": "ready" if cached else hold, **shown}
            self._coach_jobs[key] = {"state": "pending", "hash": digest}
        self.ai_jobs.submit(
            f"{key}:{digest}", lambda: self._job_coach(key, facts, digest, lang, kind)
        )
        return {"state": "pending", **shown}

    def _job_coach(
        self, key: str, facts: dict[str, Any], digest: str, lang: str, kind: str, attempt: int = 0
    ) -> None:
        client = self._coach_client()
        if client is None:
            with self._coach_lock:
                self._coach_jobs.pop(key, None)
            return
        generate = review_match if kind == "match" else review_career
        try:
            result = generate(client, facts, lang, known_items=self._known_items())
        except CoachLLMError as error:
            if error.code == "busy" and attempt < len(COACH_BUSY_RETRY_SECONDS):
                # Stays "pending" for the UI; the next try goes on the same AI thread.
                self.ai_jobs.submit(
                    f"{key}:{digest}:retry{attempt + 1}",
                    lambda: self._job_coach(key, facts, digest, lang, kind, attempt + 1),
                    delay=COACH_BUSY_RETRY_SECONDS[attempt],
                )
                return
            with self._coach_lock:
                self._coach_jobs[key] = {"state": "error", "hash": digest, "error": error.code}
            return
        except Exception:  # noqa: BLE001 - a bad answer must not kill the worker
            with self._coach_lock:
                self._coach_jobs[key] = {"state": "error", "hash": digest, "error": "bad_response"}
            return
        label = getattr(client, "label", {}) or {}
        self.store.cache_set(
            key,
            {
                "hash": digest,
                "review": result["review"],
                "provider": label.get("provider"),
                "model": label.get("model"),
                "generated_at": _now_iso(),
            },
        )
        with self._coach_lock:
            self._coach_jobs.pop(key, None)

    # --- jobs -------------------------------------------------------------------

    def request_sync(self) -> dict[str, Any]:
        primary = self.store.primary_account_id()
        if primary is None or self.client is None:
            return dict(self._sync)
        self._sync = {**self._sync, "state": "queued"}
        self.jobs.submit(f"sync:{primary}", lambda: self._job_sync(primary))
        return dict(self._sync)

    def fetch_match(self, match_id: int, *, request_parse: bool = True, delay: float = 0.0) -> None:
        primary = self.store.primary_account_id()
        if primary is None or self.client is None:
            return
        self.jobs.submit(
            f"match:{match_id}",
            lambda: self._job_fetch_match(
                primary, match_id, request_parse=request_parse, attempt=0
            ),
            delay=delay,
        )

    def _job_sync(self, account_id: int) -> None:
        client = self.client
        if client is None:
            return
        self._sync = {**self._sync, "state": "running", "error": None, "error_code": None}
        try:
            self._ensure_hero_stats()
            try:
                profile = client.player(account_id)
                self.store.upsert_player(
                    account_id,
                    source="opendota",
                    persona_name=profile.get("persona_name"),
                    avatar_url=profile.get("avatar_url"),
                    steam_id64=profile.get("steam_id64"),
                    rank_tier=profile.get("rank_tier"),
                )
            except OpenDotaError as error:
                if error.code != "private":
                    raise
            # Bot games, practice and custom lobbies would skew win rate and trends.
            recent = [
                row
                for row in client.recent_matches(account_id, limit=RECENT_MATCHES_LIMIT)
                if row.get("lobby_type") is None or row["lobby_type"] in REVIEWABLE_LOBBY_TYPES
            ]
            for row in recent:
                match_id = row.pop("match_id", None)
                if match_id:
                    self.store.upsert_match(account_id, match_id, source="opendota", fields=row)
            # Review the latest matches (one request each, well under the rate limit).
            for row in self.store.list_matches(account_id, limit=REVIEW_RECENT_MATCHES):
                if not row.get("has_analysis") or ("opendota" not in row["sources"]):
                    mid = row["match_id"]
                    self.jobs.submit(
                        f"match:{mid}",
                        lambda mid=mid: self._job_fetch_match(
                            account_id, mid, request_parse=False, attempt=0
                        ),
                    )
            self._sync = {
                "state": "done",
                "at": _now_iso(),
                "error": None,
                "error_code": None,
                "fetched": len(recent),
            }
        except OpenDotaError as error:
            self._sync = {
                "state": "error",
                "at": _now_iso(),
                "error": str(error),
                "error_code": error.code,
            }
        except Exception as error:  # noqa: BLE001 - never leave the UI stuck on "updating"
            self._sync = {
                "state": "error",
                "at": _now_iso(),
                "error": str(error),
                "error_code": "internal",
            }

    def _job_fetch_match(
        self, account_id: int, match_id: int, *, request_parse: bool, attempt: int
    ) -> None:
        client = self.client
        if client is None:
            return
        try:
            match = client.match(match_id)
        except OpenDotaError as error:
            if (
                error.code in {"not_found", "offline", "rate_limited"}
                and attempt < PARSE_POLL_ATTEMPTS
                and request_parse
            ):
                self._retry(account_id, match_id, request_parse, attempt)
            else:
                self.store.upsert_match(
                    account_id,
                    match_id,
                    source=None,
                    parse_status=f"error:{error.code}",
                )
            return
        trimmed = trim_match(match, account_id)
        if not trimmed.get("found_player"):
            self.store.upsert_match(account_id, match_id, source="opendota", parse_status="private")
            return
        parsed = bool(trimmed.get("parsed"))
        status = "parsed" if parsed else "basic"
        if not parsed and request_parse:
            if attempt == 0:
                with contextlib.suppress(OpenDotaError):
                    client.request_parse(match_id)
            status = "parsing" if attempt < PARSE_POLL_ATTEMPTS else "not_parsed"
        self.store.upsert_match(
            account_id,
            match_id,
            source="opendota",
            fields=summary_from_match(trimmed),
            opendota=trimmed,
            parse_status=status,
        )
        me = my_player(trimmed) or {}
        self._ensure_hero_meta(me.get("hero_id"))
        self._rebuild_analysis(account_id, match_id)
        if status == "parsing":
            self._retry(account_id, match_id, request_parse, attempt)

    def _retry(self, account_id: int, match_id: int, request_parse: bool, attempt: int) -> None:
        self.jobs.submit(
            f"match:{match_id}",
            lambda: self._job_fetch_match(
                account_id, match_id, request_parse=request_parse, attempt=attempt + 1
            ),
            delay=PARSE_POLL_SECONDS,
        )

    # --- reviews ---------------------------------------------------------------

    def _on_match_finished(self, timeline: dict[str, Any]) -> None:
        account_id = timeline.get("account_id") or self.store.primary_account_id()
        match_id = timeline.get("match_id")
        if not account_id or not match_id:
            return
        facts = facts_from_timeline(timeline)
        fields = {
            "hero_id": facts.get("hero_id"),
            "hero": facts.get("hero"),
            "duration": facts.get("duration"),
            "is_radiant": facts.get("is_radiant"),
            "win": facts.get("win"),
            "kills": facts.get("kills"),
            "deaths": facts.get("deaths"),
            "assists": facts.get("assists"),
            "gpm": facts.get("gpm"),
            "xpm": facts.get("xpm"),
            "last_hits": facts.get("last_hits"),
            "denies": facts.get("denies"),
            "start_time": _start_time(timeline),
        }
        self.store.upsert_match(
            account_id,
            match_id,
            source="gsi",
            fields=fields,
            timeline=timeline,
            parse_status="waiting_opendota" if self.client is not None else "gsi_only",
        )
        analysis = self._rebuild_analysis(account_id, match_id)
        # Per account: a match of another (detected, not linked) account must not
        # replace the linked player's "review ready" banner.
        self.store.set_meta(
            f"last_review:{account_id}",
            f"{match_id}|{_now_iso()}|{(analysis or {}).get('headline', {}).get('score') or ''}",
        )
        if account_id == self.store.primary_account_id():
            self.fetch_match(match_id, request_parse=True, delay=FIRST_FETCH_DELAY_SECONDS)

    def _rebuild_analysis(self, account_id: int, match_id: int) -> dict[str, Any] | None:
        record = self.store.get_match(account_id, match_id)
        if record is None:
            return None
        od = facts_from_opendota(record["opendota"]) if record.get("opendota") else None
        gsi = facts_from_timeline(record["timeline"]) if record.get("timeline") else None
        facts = merge_facts(od, gsi)
        if facts is None:
            return None
        analysis = analyze_match(
            facts, meta=self._hero_meta(facts.get("hero_id")), opendota=record.get("opendota")
        )
        lh_t = facts.get("lh_t") or []
        self.store.upsert_match(
            account_id,
            match_id,
            source=record["sources"][0] if record["sources"] else "analysis",
            fields={
                "score": analysis["headline"]["score"],
                "lh_10": lh_t[10] if len(lh_t) > 10 else None,
            },
            analysis=analysis,
        )
        return analysis

    # --- OpenDota meta data (cached; fetched on the job thread only) -----------

    def _hero_meta(self, hero_id: Any) -> dict[str, Any] | None:
        """Cached build data for a hero (stale is fine: reviews must work offline)."""
        constants = self.store.cache_get(ITEM_CONSTANTS_KEY)
        if not constants or not hero_id:
            return None
        return {
            "constants": constants,
            "popularity": self.store.cache_get(f"{POPULARITY_KEY}:{int(hero_id)}"),
            "timings": self.store.cache_get(f"{TIMINGS_KEY}:{int(hero_id)}"),
        }

    def _refresh(self, key: str, ttl: float, fetch: Callable[[], Any]) -> None:
        if self.client is None or self.store.cache_get(key, max_age=ttl) is not None:
            return
        with contextlib.suppress(OpenDotaError):
            self.store.cache_set(key, fetch())

    def _ensure_hero_meta(self, hero_id: Any) -> None:
        client = self.client
        if client is None or not hero_id:
            return
        hero = int(hero_id)
        self._refresh(ITEM_CONSTANTS_KEY, META_TTL_SECONDS, client.item_constants)
        self._refresh(
            f"{POPULARITY_KEY}:{hero}", META_TTL_SECONDS, lambda: client.item_popularity(hero)
        )
        self._refresh(f"{TIMINGS_KEY}:{hero}", META_TTL_SECONDS, lambda: client.item_timings(hero))

    def _ensure_hero_stats(self) -> None:
        client = self.client
        if client is not None:
            self._refresh(HERO_STATS_KEY, HERO_STATS_TTL_SECONDS, client.hero_stats)

    def rebuild_all(self) -> int:
        """Re-run analyses (after the rules changed)."""
        primary = self.store.primary_account_id()
        if primary is None:
            return 0
        count = 0
        for row in self.store.list_matches(primary, limit=500):
            if self._rebuild_analysis(primary, row["match_id"]) is not None:
                count += 1
        return count

    def _last_review(self) -> dict[str, Any] | None:
        primary = self.store.primary_account_id()
        if primary is None:
            return None
        raw = self.store.get_meta(f"last_review:{primary}")
        if not raw:
            return None
        match_id, at, score = (raw.split("|") + ["", "", ""])[:3]
        return {"match_id": int(match_id), "at": at, "score": int(score) if score else None}


_SUMMARY_KEYS = (
    "start_time",
    "duration",
    "hero_id",
    "hero",
    "is_radiant",
    "win",
    "kills",
    "deaths",
    "assists",
    "gpm",
    "xpm",
    "last_hits",
    "denies",
    "lh_10",
    "net_worth",
    "hero_damage",
    "lane_role",
    "game_mode",
    "lobby_type",
    "parsed",
    "score",
)


def _public_player(player: dict[str, Any] | None, account_id: int | None) -> dict[str, Any] | None:
    if account_id is None:
        return None
    player = player or {}
    return {
        "account_id": account_id,
        "steam_id64": player.get("steam_id64") or str(steam64_from_account_id(account_id)),
        "persona_name": player.get("persona_name"),
        "avatar_url": player.get("avatar_url"),
        "rank_tier": player.get("rank_tier"),
    }


def _coach_public(cached: dict[str, Any] | None, *, stale: bool) -> dict[str, Any]:
    if not cached or not cached.get("review"):
        return {}
    provider = cached.get("provider")
    return {
        "review": cached["review"],
        "provider_label": PROVIDERS[provider]["label"] if provider in PROVIDERS else provider,
        "model": cached.get("model"),
        "generated_at": cached.get("generated_at"),
        "stale": stale,
    }


def _scoreboard(trimmed: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not trimmed:
        return None
    rows = []
    for player in trimmed.get("players") or []:
        rows.append(
            {
                "me": bool(player.get("me")),
                "is_radiant": bool(player.get("isRadiant", True)),
                "hero": player.get("hero"),
                "hero_id": player.get("hero_id"),
                "name": player.get("personaname"),
                "kills": player.get("kills"),
                "deaths": player.get("deaths"),
                "assists": player.get("assists"),
                "net_worth": player.get("net_worth"),
                "gpm": player.get("gold_per_min"),
                "xpm": player.get("xp_per_min"),
                "last_hits": player.get("last_hits"),
                "hero_damage": player.get("hero_damage"),
            }
        )
    return rows


def _start_time(timeline: dict[str, Any]) -> int | None:
    started = timeline.get("started_at")
    try:
        return int(datetime.fromisoformat(str(started)).timestamp()) if started else None
    except ValueError:
        return None
