"""
main.py — FastAPI application entry point for Dota AI Coach (MVP-1).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.advice_scheduler import ADVICE_SCHEDULER, ScheduledAdvice
from app.config import GSI_STALE_SECONDS, LIVE_CONSERVATIVE_MODE, USE_LLM
from app.coach_summary import COACH_SESSION_HISTORY
from app.decision_points import detect_decision_point
from app.gsi_state import (
    get_current_state,
    get_gsi_debug_fields,
    get_gsi_debug_latest,
    update_latest_gsi,
)
from app.live_session_recorder import LIVE_SESSION_RECORDER
from app.llm_provider import generate_llm_recommendation, is_llm_provider_enabled
from app.match_memory import MATCH_MEMORY
from app.schemas import GameSituationRequest, RecommendationResponse, is_supported_hero
from app.rag import retrieve_context
from app.recommender import generate_recommendation
from app.logger import log_recommendation

app = FastAPI(
    title="Dota AI Coach",
    description="MVP-1: rule-based carry coach with local knowledge-base RAG.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
_DEMO_OVERLAY_RESPONSE: dict[str, object] | None = None
_DEMO_OVERLAY_EXPIRES_AT: datetime | None = None
_DEMO_CACHE_SECONDS = 8

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/", summary="Health check")
def root():
    """Simple health-check endpoint."""
    return {"status": "ok", "service": "Dota AI Coach", "version": "0.1.0"}


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
            if decision_point not in {"NO_ADVICE", "SOFT_STATUS"} and (not USE_LLM or not is_llm_provider_enabled())
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
        f"hp {request.hp_percent} gold {request.gold} "
        + " ".join(request.items)
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
    state = result.get("state")
    if isinstance(state, dict):
        LIVE_SESSION_RECORDER.record_gsi(payload, state)
        MATCH_MEMORY.observe_state(state)
        if is_supported_hero(str(state.get("hero") or "")):
            decision_point = detect_decision_point(state)
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
def overlay_recommendation():
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
    if not is_supported_hero(str(state.get("hero") or "")):
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

    decision_point = _live_conservative_decision_point(detect_decision_point(state), state)

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
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    state["extra_context"] = {
        **extra_context,
        "demo_replay_mode": True,
        "demo_simulation_file": str(payload.get("simulation_file") or ""),
        "demo_speed": payload.get("speed"),
    }
    demo_now = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=timestamp_seconds)
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
        scheduled.recommendation.model_dump()
        if scheduled.recommendation is not None
        else None
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
    if not is_supported_hero(str(state.get("hero") or "")):
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

    decision_point = detect_decision_point(state)

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
            fallback_reason="overlay_demo_fallback_first" if scheduled.source == "fallback" else None,
        )
        log_filename = log_path.name

    return _overlay_response(scheduled, timestamp, log_filename, state, record_history=False)


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
            "last_gsi_received_at": None,
            "seconds_since_last_gsi": None,
            "hero": demo_response.get("hero"),
            "game_time": demo_response.get("simulated_time_label") or demo_response.get("minute"),
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
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
    return {
        "gsi_connected": connected,
        "last_gsi_received_at": timestamp,
        "seconds_since_last_gsi": round(seconds_since, 2) if seconds_since is not None else None,
        "hero": state.get("hero"),
        "game_time": extra_context.get("game_time") or state.get("minute"),
        "stage": _stage_label(state) if state else "unknown",
        "received_fields": _received_gsi_fields(fields),
        "missing_important_fields": _missing_important_fields(state, fields),
        "last_advice_time": latest_advice.get("last_updated"),
        "current_advice": latest_recommendation.get("action") if isinstance(latest_recommendation, dict) else None,
        "current_mode": "live_gsi" if state else "idle",
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
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


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
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
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
    if not LIVE_CONSERVATIVE_MODE:
        return decision_point
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
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


def _overlay_live_context(state: dict[str, object]) -> dict[str, object]:
    extra_context = state.get("extra_context") if isinstance(state.get("extra_context"), dict) else {}
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
    _DEMO_OVERLAY_EXPIRES_AT = datetime.now(timezone.utc) + timedelta(seconds=_DEMO_CACHE_SECONDS)


def _get_demo_overlay_response() -> dict[str, object] | None:
    if _DEMO_OVERLAY_RESPONSE is None or _DEMO_OVERLAY_EXPIRES_AT is None:
        return None
    if datetime.now(timezone.utc) > _DEMO_OVERLAY_EXPIRES_AT:
        _clear_demo_overlay_response()
        return None
    return _DEMO_OVERLAY_RESPONSE


def _clear_demo_overlay_response() -> None:
    global _DEMO_OVERLAY_RESPONSE, _DEMO_OVERLAY_EXPIRES_AT
    _DEMO_OVERLAY_RESPONSE = None
    _DEMO_OVERLAY_EXPIRES_AT = None
