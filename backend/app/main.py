"""
main.py — FastAPI application entry point for Wardly (formerly Dota AI Coach) (MVP-1).
"""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from app.advice_i18n import localize_advice_items, localize_overlay_response, normalize_lang
from app.advice_scheduler import ADVICE_SCHEDULER, ScheduledAdvice
from app.advice_why import why
from app.coach_summary import COACH_SESSION_HISTORY
from app.config import (
    ADVICE_ROLE,
    BACKEND_PORT,
    GSI_STALE_SECONDS,
    LIVE_CONSERVATIVE_MODE,
    LLM_PROVIDER,
    MAP_HINTS,
    OPENDOTA_ENABLED,
    PLAYER_DATA_DIR,
    RESOURCE_ROOT,
    USE_LLM,
    WRITABLE_DIR,
)
from app.decision_points import detect_decision_point
from app.diagnostics import recent_errors, record_error, runtime_info
from app.game_plan import SHOW_UNTIL_CLOCK as GAME_PLAN_SHOW_UNTIL_CLOCK
from app.gsi_state import (
    get_current_state,
    get_gsi_debug_fields,
    get_gsi_debug_latest,
    is_in_match,
    post_game_match_id,
    update_latest_gsi,
)
from app.live_role import SETTINGS as ROLE_SETTINGS
from app.live_role import role_setting, set_role_setting
from app.live_session_recorder import LIVE_SESSION_RECORDER
from app.live_tools import disabled_copy
from app.llm_provider import generate_llm_recommendation, is_llm_provider_enabled
from app.logger import log_recommendation, prune_logs
from app.map_hints import map_hint, timer_strip
from app.match_memory import MATCH_MEMORY
from app.player_api import PLAYER_SERVICE
from app.player_api import router as player_router
from app.rag import retrieve_context
from app.recommender import generate_recommendation
from app.scheduler.frequency import FREQUENCIES
from app.schemas import GameSituationRequest, RecommendationResponse, hero_coverage


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    prune_logs()
    yield
    # Keeps an in-progress match timeline across a restart of the app.
    PLAYER_SERVICE.shutdown()


app = FastAPI(
    lifespan=_lifespan,
    title="Wardly",
    description="MVP-1: rule-based carry coach with local knowledge-base RAG.",
    version="0.25.0",
)
app.include_router(player_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{BACKEND_PORT}",
        f"http://localhost:{BACKEND_PORT}",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

FRONTEND_DIR = RESOURCE_ROOT / "frontend"
_DEMO_OVERLAY_RESPONSE: dict[str, object] | None = None
_DEMO_OVERLAY_EXPIRES_AT: datetime | None = None
_DEMO_CACHE_SECONDS = 8

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/", summary="Health check")
def root():
    """Simple health-check endpoint."""
    return {"status": "ok", "service": "Wardly", "version": "0.25.0"}


@app.get("/health", summary="Health check")
def health():
    """Compact health-check endpoint for local launchers and demos."""
    return {"status": "ok"}


def _build_recommendation(
    request: GameSituationRequest,
    decision_point: str | None = None,
) -> tuple[RecommendationResponse, str]:
    decision_point = decision_point or detect_decision_point(request.model_dump())

    rag_context = _retrieve_rag_context(request)

    if decision_point not in {"NO_ADVICE", "SOFT_STATUS"} and USE_LLM and is_llm_provider_enabled():
        llm_result = generate_llm_recommendation(request, decision_point, rag_context)
        if llm_result.recommendation is not None:
            log_path = log_recommendation(
                request=request,
                rag_context=rag_context,
                response=llm_result.recommendation,
                decision_point=decision_point,
                provider=llm_result.provider,
                model=llm_result.model,
            )
            return llm_result.recommendation, log_path.name

        fallback = generate_recommendation(request, rag_context)
        log_path = log_recommendation(
            request=request,
            rag_context=rag_context,
            response=fallback,
            decision_point=decision_point,
            provider=llm_result.provider,
            model=llm_result.model,
            llm_error=llm_result.error,
            fallback_reason="llm_unavailable_or_invalid",
        )
        return fallback, log_path.name

    recommendation = generate_recommendation(request, rag_context)
    log_path = log_recommendation(
        request=request,
        rag_context=rag_context,
        response=recommendation,
        decision_point=decision_point,
        provider="fallback",
        fallback_reason=(
            "llm_disabled"
            if decision_point not in {"NO_ADVICE", "SOFT_STATUS"}
            and (not USE_LLM or not is_llm_provider_enabled())
            else None
        ),
    )
    return recommendation, log_path.name


def _retrieve_rag_context(request: GameSituationRequest) -> list[str]:
    query = (
        f"{request.hero} {request.role} {request.game_state} "
        f"{request.team_status} {request.event_context} {request.item_timing_category or ''} "
        f"{request.selected_team} {request.teamfight_result} {request.objective_context} "
        f"{request.objective_type or ''} {request.objective_team or ''} "
        f"mana {request.extra_context.get('mana_percent', '')} "
        f"gpm {request.extra_context.get('gpm', '')} "
        f"last_hits {request.extra_context.get('last_hits', '')} "
        f"status {' '.join(request.extra_context.get('status_effects', [])) if isinstance(request.extra_context.get('status_effects'), list) else ''} "
        f"hero_safety {request.extra_context.get('hero_risk_level', '')} "
        f"{request.extra_context.get('hero_safety_reason', '')} "
        f"{request.extra_context.get('recommended_constraint', '')} "
        f"death_context {request.extra_context.get('last_death_context', '')} "
        f"death_pattern {request.extra_context.get('recent_death_pattern', '')} "
        f"minute {request.minute} level {request.level} "
        f"hp {request.hp_percent} gold {request.gold} " + " ".join(request.items)
    )

    rag_context = retrieve_context(
        query,
        hero=request.hero,
        game_state=request.game_state,
        owned_items=request.items,
    )
    return rag_context


@app.post("/recommend", response_model=RecommendationResponse, summary="Get a carry recommendation")
def recommend(request: GameSituationRequest):
    """
    Accept a structured game-situation description and return a carry recommendation.

    Steps:
    1. Build a query string from the request for RAG retrieval.
    2. Retrieve relevant knowledge-base paragraphs.
    3. Generate a rule-based fallback recommendation.
    4. Log the full request/context/response to disk.
    5. Return the recommendation.
    """
    recommendation, log_filename = _build_recommendation(request)
    # Attach the log filename as a response header for easy debugging
    response = JSONResponse(content=recommendation.model_dump())
    response.headers["X-Log-File"] = log_filename
    return response


@app.post("/gsi", summary="Receive Dota 2 Game State Integration data")
async def receive_gsi(request: Request):
    """Accept raw Dota 2 GSI JSON and keep the latest normalized state in memory."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "Request body must be valid JSON."},
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "GSI payload must be a JSON object."},
        )

    result = update_latest_gsi(payload)
    # Whole-match recording + Steam account detection (never breaks the live path).
    try:
        PLAYER_SERVICE.observe_gsi(payload)
    except Exception as error:  # noqa: BLE001
        print(f"[player] GSI observe failed: {error}")
        record_error("gsi-player", error)
    state = result.get("state")
    if isinstance(state, dict):
        LIVE_SESSION_RECORDER.record_gsi(payload, state)
        MATCH_MEMORY.observe_state(state)
        coverage = _advisor_coverage(state)
        if coverage:
            decision_point = _covered_decision_point(detect_decision_point(state), coverage)
            MATCH_MEMORY.last_advice_type = decision_point
            ADVICE_SCHEDULER.observe_state(state, decision_point)
        else:
            ADVICE_SCHEDULER.observe_state(state, "NO_ADVICE")
    return result


@app.get("/state/current", summary="Get latest normalized GSI state")
def current_state():
    return get_current_state()


@app.post("/session/reset", summary="Reset in-memory match session")
def reset_session():
    MATCH_MEMORY.reset()
    ADVICE_SCHEDULER.reset()
    COACH_SESSION_HISTORY.reset()
    _clear_demo_overlay_response()
    return {"status": "ok", "detail": "Match memory, overlay scheduler, and coach summary reset."}


@app.get("/session/memory", summary="Inspect safe match memory summary")
def session_memory():
    return MATCH_MEMORY.summary()


@app.get("/gsi/debug/latest", summary="Inspect latest raw and normalized GSI payload")
def gsi_debug_latest():
    return get_gsi_debug_latest()


@app.get("/gsi/debug/fields", summary="Inspect available GSI payload fields")
def gsi_debug_fields():
    return get_gsi_debug_fields()


@app.get("/gsi/status", summary="Get live GSI readiness status")
def gsi_status():
    # Polled every second by the launcher: a cheap place to close a match whose GSI stopped.
    PLAYER_SERVICE.check_stale()
    return _gsi_status_response()


@app.post("/session-recording/start", summary="Start live GSI session recording")
def start_session_recording():
    return LIVE_SESSION_RECORDER.start()


@app.post("/session-recording/stop", summary="Stop live GSI session recording")
def stop_session_recording():
    return LIVE_SESSION_RECORDER.stop()


@app.get("/session-recording/status", summary="Inspect live GSI session recording status")
def session_recording_status():
    return LIVE_SESSION_RECORDER.status()


@app.get("/overlay/recommendation", summary="Get overlay-friendly recommendation")
def overlay_recommendation(lang: str = "en"):
    """`lang=ru` returns the visible text in Russian (see app/advice_i18n.py)."""
    lang = normalize_lang(lang)
    response = localize_overlay_response(_overlay_recommendation_payload(), lang)
    plan = _game_plan_for_overlay(response, lang)
    if plan is not None:
        response = {**response, "game_plan": plan}
    post_game = _post_game_for_overlay(response, lang)
    if post_game is not None:
        response = {**response, "post_game": post_game}
    death_screen = _death_screen_for_overlay(response, lang)
    if death_screen is not None:
        response = {**response, "death_screen": death_screen}
    try:
        response = {**response, **_live_role_and_hint(response, lang)}
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("map-hint", error)
    return response


def _advisor_coverage(state: Mapping[str, object]) -> str | None:
    """hero_coverage of the live hero, with a core played as a support advised as
    a support: farm and item advice assume a core (_plays_support)."""
    coverage = hero_coverage(str(state.get("hero") or ""))
    if coverage == "full" and _plays_support(state):
        return "support"
    return coverage


def _plays_support(state: Mapping[str, object] | None) -> bool:
    state = state or {}
    raw_extra = state.get("extra_context")
    extra: Mapping[str, object] = raw_extra if isinstance(raw_extra, dict) else {}
    if extra.get("source_type") != "live_gsi":
        return False
    role = _live_role(state)
    return role is not None and role.get("role") == "support" and role.get("source") != "hero"


def _live_role(state: Mapping[str, object] | None) -> dict[str, Any] | None:
    state = state or {}
    hero = str(state.get("hero") or "")
    prior = PLAYER_SERVICE.role_prior(hero) if hero else None
    return MATCH_MEMORY.role.role(prior)


def _live_role_and_hint(response: dict[str, object], lang: str) -> dict[str, object]:
    """The player's position and the map hint (timer or role tip), live GSI only."""
    if response.get("demo_mode") or response.get("status") in {"waiting_for_gsi", "stale_gsi"}:
        return {}
    current = get_current_state()
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    extra = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    if extra.get("source_type") != "live_gsi":
        return {}
    role = _live_role(state)
    result: dict[str, object] = {"live_role": role}
    if _map_hints["enabled"]:
        clock = extra.get("clock_time")
        carry_advisor = hero_coverage(str(state.get("hero") or "")) == "full" and not (
            _plays_support(state)
        )
        last_hits = extra.get("last_hits")
        hint = map_hint(
            clock if isinstance(clock, int) else None,
            role.get("role") if role else None,
            MATCH_MEMORY.tips,
            alive=extra.get("alive") is not False,
            has_ward=extra.get("has_observer")
            if isinstance(extra.get("has_observer"), bool)
            else None,
            ward_charges=extra.get("observer_charges")
            if isinstance(extra.get("observer_charges"), int)
            else None,
            lang=lang,
            tp_missing=MATCH_MEMORY.tp.signal() is not None,
            carry_advisor=carry_advisor,
            last_hits=last_hits if isinstance(last_hits, int) else None,
            level=extra.get("hero_level") if isinstance(extra.get("hero_level"), int) else None,
            deaths=extra.get("deaths") if isinstance(extra.get("deaths"), int) else None,
            gold=state.get("gold") if isinstance(state.get("gold"), int) else None,
            lane=role.get("lane") if role else None,
            items=extra.get("item_names") if isinstance(extra.get("item_names"), list) else None,
            key_item=PLAYER_SERVICE.key_item(str(state.get("hero") or ""))
            if role and role.get("role") != "support"
            else None,
            objective=MATCH_MEMORY.roshan.hint(clock if isinstance(clock, int) else None, lang),
            skill=MATCH_MEMORY.skills.tip(
                clock if isinstance(clock, int) else None,
                lang,
                alive=extra.get("alive") is not False,
                build=PLAYER_SERVICE.skill_build(str(state.get("hero") or "")),
            ),
        )
        if hint is not None:
            result["map_hint"] = hint
        # The overlay's strip of the next events (runes, stacks, Roshan, Aegis).
        strip = timer_strip(
            clock if isinstance(clock, int) else None,
            role.get("role") if role else None,
            lang,
            MATCH_MEMORY.roshan.strip(clock if isinstance(clock, int) else None, lang),
        )
        if strip:
            result["timer_strip"] = strip
    return result


GAME_PLAN_STATUSES = {"no_advice", "monitoring", "unsupported_hero"}


def _game_plan_for_overlay(response: dict[str, object], lang: str) -> dict[str, object] | None:
    """The plan for this game while nothing else is on the card (pick to 1:30)."""
    if response.get("status") not in GAME_PLAN_STATUSES or response.get("demo_mode"):
        return None
    current = get_current_state()
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    extra = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    if extra.get("source_type") != "live_gsi":
        return None
    clock = extra.get("clock_time")
    if not isinstance(clock, int) or clock >= GAME_PLAN_SHOW_UNTIL_CLOCK:
        return None
    try:
        return PLAYER_SERVICE.game_plan(str(state.get("hero") or ""), lang)
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("game-plan", error)
        return None


def _death_screen_for_overlay(response: dict[str, object], lang: str) -> dict[str, object] | None:
    """While the player is dead (live GSI): how it happened and what to do now."""
    # A frozen "dead" snapshot must not hide the lost-connection status.
    if response.get("demo_mode") or response.get("status") in {"waiting_for_gsi", "stale_gsi"}:
        return None
    current = get_current_state()
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    extra = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    if extra.get("source_type") != "live_gsi" or extra.get("alive") is not False:
        return None
    carry = hero_coverage(str(state.get("hero") or "")) == "full" and not _plays_support(state)
    try:
        return PLAYER_SERVICE.death_screen(state, lang, next_item_for_hero=carry)
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("death-screen", error)
        return None


def _post_game_for_overlay(response: dict[str, object], lang: str) -> dict[str, object] | None:
    """The match summary while Dota shows the score screen (post_game.py)."""
    if response.get("demo_mode"):
        return None
    try:
        return PLAYER_SERVICE.post_game_card(post_game_match_id(), lang)
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("post-game", error)
        return None


def _overlay_recommendation_payload() -> dict[str, object]:
    demo_response = _get_demo_overlay_response()
    if demo_response is not None:
        return demo_response

    current = get_current_state()
    if current["status"] == "waiting_for_gsi":
        return {
            "status": "waiting_for_gsi",
            "decision_point": "NO_ADVICE",
            "recommendation": None,
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": None,
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "no_advice",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context({}),
        }

    if _is_live_gsi_stale(current):
        state = current.get("state") if isinstance(current.get("state"), dict) else {}
        return {
            "status": "stale_gsi",
            "decision_point": "NO_ADVICE",
            "recommendation": None,
            "message": "Waiting for live GSI...",
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": current.get("timestamp"),
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "stale_gsi",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            "gsi_stale": True,
            "seconds_since_last_gsi": _seconds_since_timestamp(current.get("timestamp")),
            **_overlay_live_context(state),
        }

    state = current["state"] or {}
    coverage = _advisor_coverage(state)
    if not coverage:
        ADVICE_SCHEDULER.observe_state(state, "NO_ADVICE")
        return {
            "status": "unsupported_hero",
            "decision_point": "NO_ADVICE",
            "recommendation": None,
            "message": "Current hero is not supported by carry advisor yet.",
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": current["timestamp"],
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "unsupported_hero",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    decision_point = _covered_decision_point(
        _useful_disable(
            _live_conservative_decision_point(detect_decision_point(state), state), state
        ),
        coverage,
    )

    if decision_point == "NO_ADVICE":
        ADVICE_SCHEDULER.observe_state(state, decision_point)
        active = ADVICE_SCHEDULER.active_advice_for_state(state, decision_point)
        if active is not None:
            return _overlay_response(active, current["timestamp"], state=state)
        return {
            "status": "no_advice",
            "decision_point": decision_point,
            "recommendation": None,
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": current["timestamp"],
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "no_advice",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    if decision_point == "SOFT_STATUS":
        ADVICE_SCHEDULER.observe_state(state, decision_point)
        active = ADVICE_SCHEDULER.active_advice_for_state(state, decision_point)
        if active is not None:
            return _overlay_response(active, current["timestamp"], state=state)
        return {
            "status": "monitoring",
            "decision_point": decision_point,
            "recommendation": None,
            "message": "Monitoring lane — no urgent advice.",
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": current["timestamp"],
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": None,
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    state = _with_next_item(state, coverage, decision_point)
    state = _with_death_items(state, decision_point)
    state = _with_coverage(state, coverage)
    try:
        request = GameSituationRequest(**state)
    except ValidationError as exc:
        return {
            "status": "invalid_state",
            "decision_point": decision_point,
            "recommendation": None,
            "advice_count": ADVICE_SCHEDULER.stats()["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": current["timestamp"],
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": None,
            "detail": exc.errors(include_context=False),
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    rag_context = _retrieve_rag_context(request)
    scheduled = ADVICE_SCHEDULER.evaluate(request, decision_point, rag_context)

    log_filename = None
    if scheduled.new_advice and scheduled.recommendation is not None:
        log_path = log_recommendation(
            request=request,
            rag_context=rag_context,
            response=scheduled.recommendation,
            decision_point=decision_point,
            provider=scheduled.source,
            fallback_reason="overlay_fallback_first" if scheduled.source == "fallback" else None,
        )
        log_filename = log_path.name
        # The post-match review lists the advice given in this match.
        try:
            extra = (
                state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
            )
            PLAYER_SERVICE.note_live_advice(
                extra.get("clock_time"),
                decision_point,
                scheduled.recommendation.action,
                scheduled.recommendation.reason,
                scheduled.advice_mode,
            )
        except Exception as error:  # noqa: BLE001 - never breaks the live path
            record_error("advice-note", error)

    return _overlay_response(scheduled, current["timestamp"], log_filename, state)


@app.post("/demo/replay-state", summary="Inject one replay-derived state for overlay demo")
async def demo_replay_state(request: Request):
    """Accept one GSI-like replay state and update the overlay through the real advice path."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "Request body must be valid JSON."},
        )

    if not isinstance(payload, dict) or not isinstance(payload.get("state"), dict):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": "Payload must contain a state object."},
        )

    timestamp_seconds = _safe_int(payload.get("timestamp_seconds"), 0)
    state = dict(payload["state"])
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    state["extra_context"] = {
        **extra_context,
        "demo_replay_mode": True,
        "demo_simulation_file": str(payload.get("simulation_file") or ""),
        "demo_speed": payload.get("speed"),
    }
    demo_now = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=timestamp_seconds)
    timestamp = demo_now.isoformat()

    MATCH_MEMORY.observe_state(state)
    response = _overlay_response_for_state(state, timestamp=timestamp, now=demo_now)
    response.update(
        {
            "demo_mode": True,
            "simulated_timestamp_seconds": timestamp_seconds,
            "simulated_time_label": _format_game_time(timestamp_seconds),
        }
    )
    COACH_SESSION_HISTORY.record_overlay_advice(response, state)
    _set_demo_overlay_response(response)
    return {"status": "ok", "overlay": response}


@app.get("/demo/session-summary", summary="Get coach-style summary for the current demo/session")
def demo_session_summary():
    return COACH_SESSION_HISTORY.build_summary(ADVICE_SCHEDULER.stats())


@app.get("/advice/recent", summary="Get the most recent advice shown in this session")
def recent_advice(limit: int = 5, lang: str = "en"):
    """Newest first; used by the launcher's "Recent advice" card."""
    limit = max(1, min(int(limit), 20))
    records = COACH_SESSION_HISTORY.records()[-limit:]
    return {
        "items": localize_advice_items(
            [
                {
                    "timestamp": record.get("timestamp"),
                    "game_time": record.get("game_time") or None,
                    "hero": record.get("hero"),
                    "action": record.get("action"),
                    "reason": record.get("reason"),
                    "priority": record.get("priority"),
                    "advice_mode": record.get("advice_mode"),
                    "why": why(record.get("decision_point"), normalize_lang(lang)),
                }
                for record in reversed(records)
            ],
            normalize_lang(lang),
        )
    }


class AdviceSettings(BaseModel):
    frequency: str | None = None
    role: str | None = None
    map_hints: bool | None = None


# Map hints (timers, role tips) on the overlay; the launcher switches them.
_map_hints = {"enabled": MAP_HINTS}
set_role_setting(ADVICE_ROLE)


def _advice_settings() -> dict[str, object]:
    return {
        "frequency": ADVICE_SCHEDULER.frequency,
        "options": list(FREQUENCIES),
        "role": role_setting(),
        "role_options": list(ROLE_SETTINGS),
        "map_hints": _map_hints["enabled"],
    }


@app.get("/settings/advice", summary="Live advice preferences")
def get_advice_settings():
    return _advice_settings()


@app.post("/settings/advice", summary="Change live advice preferences")
def set_advice_settings(settings: AdviceSettings):
    if settings.frequency is not None:
        ADVICE_SCHEDULER.set_frequency(settings.frequency)
    if settings.role is not None:
        set_role_setting(settings.role)
    if settings.map_hints is not None:
        _map_hints["enabled"] = bool(settings.map_hints)
    return _advice_settings()


@app.get("/diagnostics", summary="State and recent errors for a problem report")
def diagnostics():
    """No keys and no raw GSI: what a tester can safely send to the developer."""
    records = COACH_SESSION_HISTORY.records()[-10:]
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "runtime": runtime_info(),
        "config": {
            "use_llm": USE_LLM,
            "llm_provider": LLM_PROVIDER,
            "live_conservative_mode": LIVE_CONSERVATIVE_MODE,
            "gsi_stale_seconds": GSI_STALE_SECONDS,
            "opendota_enabled": OPENDOTA_ENABLED,
            "writable_dir": str(WRITABLE_DIR),
            "player_data_dir": str(PLAYER_DATA_DIR),
        },
        "gsi": _gsi_status_response(),
        "scheduler": {**ADVICE_SCHEDULER.stats(), "frequency": ADVICE_SCHEDULER.frequency},
        "recent_advice": [
            {
                key: record.get(key)
                for key in ("timestamp", "game_time", "hero", "action", "priority", "advice_mode")
            }
            for record in reversed(records)
        ],
        "player": PLAYER_SERVICE.diagnostics(),
        "errors": recent_errors(),
    }


@app.get("/overlay/stats", summary="Get overlay advice scheduler telemetry")
def overlay_stats():
    return ADVICE_SCHEDULER.stats()


@app.get("/overlay/debug/state_machine", summary="Inspect live overlay advice state machine")
def overlay_state_machine_debug():
    current = get_current_state()
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    decision_point = detect_decision_point(state) if state else "NO_ADVICE"
    return ADVICE_SCHEDULER.state_machine_debug(
        current_decision_point=decision_point,
        state=state,
    )


def _overlay_response(
    scheduled: ScheduledAdvice,
    gsi_timestamp: str | None,
    log_filename: str | None = None,
    state: dict[str, object] | None = None,
    record_history: bool = True,
) -> dict[str, object]:
    recommendation = (
        scheduled.recommendation.model_dump() if scheduled.recommendation is not None else None
    )
    response: dict[str, object] = {
        "status": scheduled.status,
        "decision_point": scheduled.decision_point,
        "recommendation": recommendation,
        "advice_count": scheduled.advice_count,
        "llm_used": scheduled.llm_used,
        "source": scheduled.source,
        "last_updated": scheduled.last_updated or gsi_timestamp,
        "next_allowed_advice_in_seconds": scheduled.next_allowed_advice_in_seconds,
        "advice_mode": scheduled.advice_mode,
        "suppressed_reason": scheduled.suppressed_reason,
        "message": _overlay_status_message(scheduled),
        "active_advice_until": scheduled.active_advice_until,
        "last_visible_advice": scheduled.last_visible_advice,
        "is_pinned": scheduled.is_pinned,
        "new_advice": scheduled.new_advice,
        "game_time_gap_since_previous_advice": scheduled.game_time_gap_since_previous_advice,
        "suppressed_by_game_time_spacing": scheduled.suppressed_by_game_time_spacing,
        "timestamp": gsi_timestamp,
        "event": scheduled.decision_point,
        **_overlay_live_context(state or {}),
    }
    if log_filename:
        response["log_file"] = log_filename
    if record_history:
        COACH_SESSION_HISTORY.record_overlay_advice(response, state or {})
        LIVE_SESSION_RECORDER.record_advice(response, state or {})
    return {
        **response,
    }


def _overlay_response_for_state(
    state: dict[str, object],
    *,
    timestamp: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    coverage = hero_coverage(str(state.get("hero") or ""))
    if not coverage:
        ADVICE_SCHEDULER.observe_state(state, "NO_ADVICE", now=now)
        return {
            "status": "unsupported_hero",
            "decision_point": "NO_ADVICE",
            "recommendation": None,
            "message": "Current hero is not supported by carry advisor yet.",
            "advice_count": ADVICE_SCHEDULER.stats(now=now)["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": timestamp,
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "unsupported_hero",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    decision_point = _covered_decision_point(detect_decision_point(state), coverage)

    if decision_point == "NO_ADVICE":
        ADVICE_SCHEDULER.observe_state(state, decision_point, now=now)
        active = ADVICE_SCHEDULER.active_advice_for_state(state, decision_point, now=now)
        if active is not None:
            return _overlay_response(active, timestamp, state=state, record_history=False)
        return {
            "status": "no_advice",
            "decision_point": decision_point,
            "recommendation": None,
            "advice_count": ADVICE_SCHEDULER.stats(now=now)["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": timestamp,
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": "no_advice",
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    if decision_point == "SOFT_STATUS":
        ADVICE_SCHEDULER.observe_state(state, decision_point, now=now)
        active = ADVICE_SCHEDULER.active_advice_for_state(state, decision_point, now=now)
        if active is not None:
            return _overlay_response(active, timestamp, state=state, record_history=False)
        return {
            "status": "monitoring",
            "decision_point": decision_point,
            "recommendation": None,
            "message": "Monitoring lane — no urgent advice.",
            "advice_count": ADVICE_SCHEDULER.stats(now=now)["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": timestamp,
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": None,
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    state = _with_next_item(state, coverage, decision_point)
    state = _with_death_items(state, decision_point)
    state = _with_coverage(state, coverage)
    try:
        game_request = GameSituationRequest(**state)
    except ValidationError as exc:
        return {
            "status": "invalid_state",
            "decision_point": decision_point,
            "recommendation": None,
            "advice_count": ADVICE_SCHEDULER.stats(now=now)["advice_count"],
            "llm_used": False,
            "source": "none",
            "last_updated": timestamp,
            "next_allowed_advice_in_seconds": 0,
            "advice_mode": "status",
            "suppressed_reason": None,
            "detail": exc.errors(include_context=False),
            "active_advice_until": None,
            "last_visible_advice": None,
            "is_pinned": False,
            **_overlay_live_context(state),
        }

    rag_context = _retrieve_rag_context(game_request)
    scheduled = ADVICE_SCHEDULER.evaluate(game_request, decision_point, rag_context, now=now)
    log_filename = None
    if scheduled.new_advice and scheduled.recommendation is not None:
        log_path = log_recommendation(
            request=game_request,
            rag_context=rag_context,
            response=scheduled.recommendation,
            decision_point=decision_point,
            provider=scheduled.source,
            fallback_reason="overlay_demo_fallback_first"
            if scheduled.source == "fallback"
            else None,
        )
        log_filename = log_path.name

    return _overlay_response(scheduled, timestamp, log_filename, state, record_history=False)


# Decisions that can become the post-laning "safe farm route" advice.
FARM_ROUTE_DECISIONS = {"SAFE_FARMING", "LANING_FARM_CHECK", "FARMING_PHASE_PRESSURE"}


def _with_next_item(
    state: dict[str, object], coverage: str | None, decision_point: str
) -> dict[str, object]:
    """A core's farm advice names the next item of the hero's usual build and the
    gold it still needs (app/next_item.py, post_laning_coach._next_item_copy)."""
    raw_extra = state.get("extra_context")
    if (
        decision_point not in FARM_ROUTE_DECISIONS
        or coverage != "full"
        or not isinstance(raw_extra, dict)
        or _plays_support(state)
    ):
        return state
    names = raw_extra.get("item_names")
    try:
        item = PLAYER_SERVICE.next_item(
            str(state.get("hero") or ""), names if isinstance(names, list) else None
        )
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("next-item", error)
        return state
    if item is None:
        return state
    return {**state, "extra_context": {**raw_extra, "next_item": item}}


def _with_coverage(state: dict[str, object], coverage: str | None) -> dict[str, object]:
    """The advisor coverage for the scheduler: its heartbeat names the farm pace
    and the kill score only for a core (post_laning_coach._situational_farm_copy)."""
    raw_extra = state.get("extra_context")
    if not isinstance(raw_extra, dict):
        return state
    return {**state, "extra_context": {**raw_extra, "advisor_coverage": coverage}}


# Death reviews: the advice after a death names the rescue item left unpressed.
DEATH_DECISIONS = {
    "DEATH_REVIEW",
    "REPEATED_DEATH_PATTERN",
    "DEATH_WITH_ESCAPE_ON_COOLDOWN",
    "DEATH_LOW_RESOURCE",
    "DEAD_WAIT",
}


def _with_death_items(state: dict[str, object], decision_point: str) -> dict[str, object]:
    """The rescue items ready in the last seconds before this death (the match
    recording's last_moments) and where it happened, for live_tools.death_copy."""
    raw_extra = state.get("extra_context")
    if decision_point not in DEATH_DECISIONS or not isinstance(raw_extra, dict):
        return state
    try:
        death = PLAYER_SERVICE.recent_death(raw_extra.get("clock_time"))
    except Exception as error:  # noqa: BLE001 - never breaks the live path
        record_error("death-items", error)
        return state
    if not death:
        return state
    added = {"death_items": death["items"], "death_place": death["place"]}
    return {**state, "extra_context": {**raw_extra, **added}}


def _overlay_status_message(scheduled: ScheduledAdvice) -> str | None:
    if scheduled.status == "active_advice":
        return None
    if scheduled.status == "cooldown":
        return "Monitoring..."
    if scheduled.status == "no_advice":
        return "Monitoring lane — no urgent advice."
    return None


def _gsi_status_response() -> dict[str, object]:
    demo_response = _get_demo_overlay_response()
    if demo_response is not None:
        return {
            "gsi_connected": False,
            "in_match": False,
            "last_gsi_received_at": None,
            "seconds_since_last_gsi": None,
            "hero": demo_response.get("hero"),
            "game_time": demo_response.get("simulated_time_label") or demo_response.get("minute"),
            "clock_time": None,
            "stage": demo_response.get("stage", "unknown"),
            "received_fields": [],
            "missing_important_fields": [],
            "last_advice_time": demo_response.get("last_updated"),
            "current_mode": "demo_replay",
        }

    current = get_current_state()
    timestamp = current.get("timestamp")
    state = current.get("state") if isinstance(current.get("state"), dict) else {}
    seconds_since = _seconds_since_timestamp(timestamp)
    connected = seconds_since is not None and seconds_since <= GSI_STALE_SECONDS
    fields = get_gsi_debug_fields()
    latest_advice = ADVICE_SCHEDULER.latest_advice_snapshot()
    latest_recommendation = latest_advice.get("recommendation")
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    return {
        "gsi_connected": connected,
        "in_match": connected and is_in_match(),
        # The score screen with a fresh review: the overlay shows the summary card.
        "post_game": connected and _post_game_for_overlay({}, "en") is not None,
        "last_gsi_received_at": timestamp,
        "seconds_since_last_gsi": round(seconds_since, 2) if seconds_since is not None else None,
        "hero": state.get("hero"),
        "hero_coverage": _advisor_coverage(state) if state else None,
        "game_time": extra_context.get("game_time") or state.get("minute"),
        # The in-game clock as the player sees it (negative before the horn).
        "clock_time": extra_context.get("clock_time"),
        "stage": _stage_label(state) if state else "unknown",
        "received_fields": _received_gsi_fields(fields),
        "missing_important_fields": _missing_important_fields(state, fields),
        "last_advice_time": latest_advice.get("last_updated"),
        "current_advice": latest_recommendation.get("action")
        if isinstance(latest_recommendation, dict)
        else None,
        "current_mode": "live_gsi" if state else "idle",
        "live_role": _live_role(state) if extra_context.get("source_type") == "live_gsi" else None,
    }


def _is_live_gsi_stale(current: dict[str, object]) -> bool:
    seconds_since = _seconds_since_timestamp(current.get("timestamp"))
    return seconds_since is not None and seconds_since > GSI_STALE_SECONDS


def _seconds_since_timestamp(timestamp: object) -> float | None:
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(timestamp))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - parsed).total_seconds())


def _received_gsi_fields(fields: dict[str, object]) -> list[str]:
    received: list[str] = []
    for name in ("map", "player", "hero", "items", "abilities", "buildings", "draft"):
        if fields.get(f"has_{name}"):
            received.append(name)
    for block_name, field_name in (
        ("map", "available_map_fields"),
        ("player", "available_player_fields"),
        ("hero", "available_hero_fields"),
    ):
        values = fields.get(field_name)
        if isinstance(values, list):
            received.extend(f"{block_name}.{value}" for value in values)
    return sorted(set(received))


def _missing_important_fields(state: dict[str, object], fields: dict[str, object]) -> list[str]:
    missing: list[str] = []
    for name in ("map", "player", "hero", "items"):
        if not fields.get(f"has_{name}"):
            missing.append(name)
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    important_context = {
        "hero.health": state.get("hp_percent"),
        "hero.mana": extra_context.get("mana_percent"),
        "player.last_hits": extra_context.get("last_hits"),
        "hero.alive": extra_context.get("alive"),
        "map.game_time": extra_context.get("game_time"),
        "abilities": extra_context.get("abilities") if extra_context.get("has_abilities") else None,
    }
    missing.extend(name for name, value in important_context.items() if value is None)
    return sorted(set(missing))


def _live_conservative_decision_point(decision_point: str, state: dict[str, object]) -> str:
    # Intentional trade-off (do not "fix"): in live GSI mode we deliberately
    # downgrade OBJECTIVE_FIGHT_CHECK to SOFT_STATUS whenever the local GSI
    # payload is missing nearby_allies_enemies / enemy_positions /
    # exact_teamfight_context, or context_confidence != "high" - even if the
    # team appears fully alive. Live GSI cannot confirm team readiness, so we
    # refuse to escalate toward an objective call without those signals. This is
    # intentional conservatism (under-advice over wrong objective calls),
    # documented in AGENTS.md. Phase 3 records the trade-off without changing it.
    if not LIVE_CONSERVATIVE_MODE:
        return decision_point
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    if extra_context.get("source_type") != "live_gsi":
        return decision_point
    if decision_point != "OBJECTIVE_FIGHT_CHECK":
        return decision_point
    missing_signals = extra_context.get("missing_signals")
    if not isinstance(missing_signals, list):
        missing_signals = []
    if (
        "nearby_allies_enemies" in missing_signals
        or "enemy_positions" in missing_signals
        or "exact_teamfight_context" in missing_signals
        or extra_context.get("context_confidence") != "high"
    ):
        return "SOFT_STATUS"
    return decision_point


def _useful_disable(decision_point: str, state: dict[str, object]) -> str:
    """Live GSI: a disable card only when something can be pressed as it ends (or
    now, when only silenced or muted) — live_tools.disabled_copy. «Wait out the
    disable» alone was up to 40 % of the urgent cards and changes nothing."""
    if decision_point != "DISABLED_STATUS":
        return decision_point
    raw_extra = state.get("extra_context")
    extra: dict[str, object] = raw_extra if isinstance(raw_extra, dict) else {}
    if extra.get("source_type") != "live_gsi":
        return decision_point
    if disabled_copy(extra, state.get("hero")) is None:
        return "NO_ADVICE"
    return decision_point


# Heroes outside the advisor get only what is true for any hero: survival,
# deaths, disables, mana, buyback. Farm, item, objective and hero-ability advice
# assume a core (or a hero profile) and stay off for them.
SAFETY_ONLY_DECISIONS = {
    "LOW_HP",
    "LOW_HP_WARNING",
    "RECENT_DAMAGE_WARNING",
    "OVERSTAY_WARNING",
    "DEATH_REVIEW",
    "REPEATED_DEATH_PATTERN",
    "DEATH_WITH_ESCAPE_ON_COOLDOWN",
    "DEATH_LOW_RESOURCE",
    "DISABLED_STATUS",
    "DEAD_WAIT",
    "LOW_MANA",
    "BUYBACK_AVAILABLE",
    "SMOKED_STATUS",
    "NO_ADVICE",
    "SOFT_STATUS",
}


# A support (a profiled one, or a core played as a support) also gets its own
# saves (hero safety, ability cooldowns), fights and objectives and the lane regen
# check; farm pace and items stay off — a support's gold and last hits are the
# map tips' business (stacks, pulls, wards, save items).
SUPPORT_DECISIONS = SAFETY_ONLY_DECISIONS | {
    "HERO_SURVIVABILITY_RISK",
    "ABILITY_SAFETY_COOLDOWN",
    "OBJECTIVE_FIGHT_CHECK",
    "BAD_FIGHT_RISK",
    "LANING_REGEN_CHECK",
}


def _covered_decision_point(decision_point: str, coverage: str | None) -> str:
    if coverage == "safety" and decision_point not in SAFETY_ONLY_DECISIONS:
        return "NO_ADVICE"
    if coverage == "support" and decision_point not in SUPPORT_DECISIONS:
        return "NO_ADVICE"
    return decision_point


def _overlay_live_context(state: dict[str, object]) -> dict[str, object]:
    extra_context = (
        state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    )
    status_effects = extra_context.get("status_effects")
    if not isinstance(status_effects, list):
        status_effects = []
    hero_safety_flags = extra_context.get("hero_safety_flags")
    if not isinstance(hero_safety_flags, list):
        hero_safety_flags = []
    return {
        "current_mode": "live_gsi" if extra_context.get("source_type") == "live_gsi" else "idle",
        "live_conservative_mode": LIVE_CONSERVATIVE_MODE,
        "hero": state.get("hero"),
        "hero_coverage": _advisor_coverage(state),
        "minute": state.get("minute"),
        "stage": _stage_label(state),
        "game_state": state.get("game_state"),
        "hp_percent": state.get("hp_percent"),
        "mana_percent": extra_context.get("mana_percent"),
        "alive": extra_context.get("alive"),
        "respawn_seconds": extra_context.get("respawn_seconds"),
        "gpm": extra_context.get("gpm"),
        "xpm": extra_context.get("xpm"),
        "last_hits": extra_context.get("last_hits"),
        "status_effects": status_effects,
        "smoked": extra_context.get("smoked", False),
        "buyback_available": extra_context.get("buyback_available", False),
        "hero_safety_flags": hero_safety_flags,
        "hero_risk_level": extra_context.get("hero_risk_level", "low"),
        "hero_safety_reason": extra_context.get("hero_safety_reason", ""),
        "capability_source": extra_context.get("capability_source"),
        "source_type": extra_context.get("source_type"),
        "context_confidence": extra_context.get("context_confidence"),
        "farm_quality": extra_context.get("farm_quality"),
        "hp_pressure_state": extra_context.get("hp_pressure_state"),
        "position_zone": extra_context.get("position_zone"),
        "position_risk": extra_context.get("position_risk"),
        "laning_category": extra_context.get("laning_category"),
        "post_laning_category": extra_context.get("post_laning_category"),
        "available_signals": extra_context.get("available_signals", []),
        "missing_signals": extra_context.get("missing_signals", []),
        "partial_signals": extra_context.get("partial_signals", []),
        **MATCH_MEMORY.overlay_context(),
    }


def _stage_label(state: dict[str, object]) -> str:
    minute = _safe_int(state.get("minute"), 0)
    if minute < 10:
        return "laning"
    if minute < 20:
        return "post-laning"
    return "macro"


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_game_time(timestamp_seconds: int) -> str:
    timestamp_seconds = max(0, int(timestamp_seconds))
    return f"{timestamp_seconds // 60:02d}:{timestamp_seconds % 60:02d}"


def _set_demo_overlay_response(response: dict[str, object]) -> None:
    global _DEMO_OVERLAY_RESPONSE, _DEMO_OVERLAY_EXPIRES_AT
    _DEMO_OVERLAY_RESPONSE = response
    _DEMO_OVERLAY_EXPIRES_AT = datetime.now(UTC) + timedelta(seconds=_DEMO_CACHE_SECONDS)


def _get_demo_overlay_response() -> dict[str, object] | None:
    if _DEMO_OVERLAY_RESPONSE is None or _DEMO_OVERLAY_EXPIRES_AT is None:
        return None
    if datetime.now(UTC) > _DEMO_OVERLAY_EXPIRES_AT:
        _clear_demo_overlay_response()
        return None
    return _DEMO_OVERLAY_RESPONSE


def _clear_demo_overlay_response() -> None:
    global _DEMO_OVERLAY_RESPONSE, _DEMO_OVERLAY_EXPIRES_AT
    _DEMO_OVERLAY_RESPONSE = None
    _DEMO_OVERLAY_EXPIRES_AT = None
