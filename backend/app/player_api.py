"""
player_api.py - HTTP endpoints for the linked player, matches and reviews.

GET    /player                   account, sync state, live match, last review
POST   /player/link              {"steam": "<Steam ID / Friend ID / profile link>"}
POST   /player/link-detected     link the account currently seen in GSI
DELETE /player                   forget the linked account (matches stay stored)
POST   /player/sync              pull profile + recent matches from OpenDota
GET    /player/matches           match table (newest first; ?hero_id=&result=win|loss)
GET    /player/matches/{id}      one match: summary, scoreboard, post-match review
POST   /player/matches/{id}/refresh   fetch again / ask OpenDota to parse the replay
GET    /player/career            statistics and advice over the recent matches
POST   /player/matches/{id}/coach     (re)generate the AI coach review of a match
POST   /player/career/coach           (re)generate the AI coach review of recent matches
GET    /player/opendota          OpenDota key status (never returns the key)
POST   /player/opendota          {"api_key": "..."}: faster, higher OpenDota limits
DELETE /player/opendota          forget the OpenDota key
GET    /player/ai                AI coach settings (never returns the key)
POST   /player/ai                {"provider": "groq"|"openrouter", "api_key": "...", "model"?}
DELETE /player/ai                forget the key
POST   /player/ai/check          one small request to validate the key

All review texts follow `lang` (ru/en).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.advice_i18n import normalize_lang
from app.coach_llm import env_settings
from app.config import OPENDOTA_API_KEY, OPENDOTA_API_URL, OPENDOTA_ENABLED, PLAYER_DATA_DIR
from app.history_backup import BackupError
from app.opendota import OpenDotaClient
from app.player_service import PlayerService
from app.steam_ids import SteamIdError

PLAYER_SERVICE = PlayerService(
    PLAYER_DATA_DIR,
    client=OpenDotaClient(OPENDOTA_API_URL, api_key=OPENDOTA_API_KEY) if OPENDOTA_ENABLED else None,
    env_ai=env_settings(),
)

router = APIRouter(prefix="/player", tags=["player"])

# Match ids are stored as SQLite INTEGER (64-bit): bigger ids are a 422, not a 500.
MatchId = Annotated[int, Path(ge=0, le=2**63 - 1)]
HeroId = Annotated[int | None, Query(ge=0, le=100_000)]
Offset = Annotated[int, Query(ge=0, le=10_000_000)]


class LinkRequest(BaseModel):
    steam: str


class OpenDotaKeyRequest(BaseModel):
    api_key: str


class AskRequest(BaseModel):
    question: str


class FocusRequest(BaseModel):
    finding_id: str


class AIRequest(BaseModel):
    provider: str
    api_key: str
    model: str | None = None


@router.get("", summary="Linked player and sync status")
def player_status():
    return PLAYER_SERVICE.status()


@router.post("/link", summary="Link a Steam account")
def link_player(request: LinkRequest):
    try:
        return PLAYER_SERVICE.link(request.steam)
    except SteamIdError as error:
        return JSONResponse(
            status_code=400, content={"status": "error", "code": error.code, "detail": str(error)}
        )


@router.post("/link-detected", summary="Link the account currently playing (from GSI)")
def link_detected():
    detected = PLAYER_SERVICE.status().get("detected")
    if not detected:
        return JSONResponse(
            status_code=404, content={"status": "error", "code": "no_detected_account"}
        )
    return PLAYER_SERVICE.link(str(detected["account_id"]))


@router.delete("", summary="Forget the linked account")
def unlink_player():
    return PLAYER_SERVICE.unlink()


@router.post("/sync", summary="Pull profile and recent matches from OpenDota")
def sync_player():
    return {"sync": PLAYER_SERVICE.request_sync(), "opendota": PLAYER_SERVICE.client is not None}


@router.get("/matches", summary="Match table of the linked player")
def player_matches(
    limit: int = 50, offset: Offset = 0, hero_id: HeroId = None, result: str | None = None
):
    """`hero_id` and `result` (win | loss) filter the table."""
    limit = max(1, min(int(limit), 200))
    win = {"win": True, "loss": False}.get(str(result or "").lower())
    return PLAYER_SERVICE.list_matches(
        limit=limit, offset=max(0, int(offset)), hero_id=hero_id, win=win
    )


@router.get("/matches/{match_id}", summary="Post-match review")
def player_match(match_id: MatchId, lang: str = "en"):
    detail = PLAYER_SERVICE.match_detail(match_id, normalize_lang(lang))
    if detail is None:
        return JSONResponse(status_code=404, content={"status": "error", "code": "match_not_found"})
    return detail


@router.post(
    "/matches/{match_id}/refresh", summary="Fetch the match again and request a replay parse"
)
def refresh_match(match_id: MatchId):
    PLAYER_SERVICE.fetch_match(match_id, request_parse=True)
    return {"status": "queued", "opendota": PLAYER_SERVICE.client is not None}


@router.get("/matches/{match_id}/share", summary="The public part of a review, to share")
def share_payload(match_id: MatchId, lang: str = "en", coach: bool = False):
    review = PLAYER_SERVICE.share_payload(match_id, normalize_lang(lang), with_coach=coach)
    if review is None:
        return JSONResponse(status_code=404, content={"status": "error", "code": "no_review"})
    return {"review": review}


@router.get("/career/share", summary="The public part of Progress, to share")
def share_progress(lang: str = "en", coach: bool = False):
    progress = PLAYER_SERVICE.share_progress_payload(normalize_lang(lang), with_coach=coach)
    if progress is None:
        return JSONResponse(status_code=404, content={"status": "error", "code": "no_progress"})
    return {"progress": progress}


@router.get("/week", summary="The last seven days for the home screen")
def player_week(
    lang: str = "en",
    until: Annotated[float | None, Query(gt=0, lt=1e11)] = None,
    since: Annotated[float | None, Query(gt=0, lt=1e11)] = None,
):
    if since is not None and (until is None or not until - 8 * 86400 <= since < until):
        return JSONResponse(status_code=422, content={"status": "error", "code": "bad_period"})
    return {"week": PLAYER_SERVICE.week(normalize_lang(lang), until, since)}


@router.get("/session", summary="The games of the latest sitting («итог вечера»)")
def player_session(lang: str = "en"):
    return {"session": PLAYER_SERVICE.session(normalize_lang(lang))}


@router.get("/usage", summary="Advice counts of a period for the opt-in anonymous statistics")
def player_usage(
    since: Annotated[float, Query(gt=0, lt=1e11)],
    until: Annotated[float, Query(gt=0, lt=1e11)],
):
    if not until - 8 * 86400 <= since < until:
        return JSONResponse(status_code=422, content={"status": "error", "code": "bad_period"})
    return {"usage": PLAYER_SERVICE.usage(int(since), int(until))}


@router.get("/backup", summary="The whole history as one backup (no keys)")
def export_history(request: Request):
    return PLAYER_SERVICE.export_backup(str(request.app.version))


@router.post("/backup", summary="Merge a history backup (adds, never overwrites)")
def import_history(data: Annotated[dict, Body()]):
    try:
        return PLAYER_SERVICE.import_backup(data)
    except BackupError as error:
        return JSONResponse(
            status_code=400, content={"status": "error", "code": error.code, "detail": str(error)}
        )


class FriendRequest(BaseModel):
    steam: str


@router.get("/friend", summary="The player next to a friend (OpenDota)")
def friend_compare(lang: str = "en", group: str = "all"):
    return PLAYER_SERVICE.friend(normalize_lang(lang), group)


@router.post("/friend", summary="Compare with a friend (Steam ID, Friend ID or profile link)")
def set_friend(request: FriendRequest, lang: str = "en"):
    try:
        return PLAYER_SERVICE.set_friend(request.steam, normalize_lang(lang))
    except SteamIdError as error:
        return JSONResponse(
            status_code=400, content={"status": "error", "code": error.code, "detail": str(error)}
        )


@router.post("/friend/refresh", summary="Fetch the friend's matches again")
def refresh_friend(lang: str = "en"):
    return PLAYER_SERVICE.refresh_friend(normalize_lang(lang))


@router.delete("/friend", summary="Stop comparing with the friend")
def remove_friend():
    return PLAYER_SERVICE.remove_friend()


@router.get("/career", summary="Statistics and advice over recent matches")
def player_career(lang: str = "en", hero_id: HeroId = None):
    """`hero_id` narrows the progress to one hero (no AI review then)."""
    return PLAYER_SERVICE.career(normalize_lang(lang), hero_id=hero_id)


@router.post("/matches/{match_id}/ask", summary="Ask the AI coach a question about a match")
def ask_match(match_id: MatchId, request: AskRequest, lang: str = "en"):
    """Answered synchronously (up to about a minute); the answer is fact-checked."""
    return PLAYER_SERVICE.ask_match(match_id, request.question, normalize_lang(lang))


@router.post("/focus", summary="Work on one recurring problem from now on")
def set_focus(request: FocusRequest, lang: str = "en"):
    try:
        PLAYER_SERVICE.set_focus(request.finding_id)
    except ValueError as error:
        return JSONResponse(status_code=400, content={"status": "error", "code": str(error)})
    return PLAYER_SERVICE.focus_status(normalize_lang(lang))


@router.delete("/focus", summary="Stop tracking the focus problem")
def clear_focus():
    PLAYER_SERVICE.clear_focus()
    return {"status": "ok"}


@router.post("/matches/{match_id}/coach", summary="(Re)generate the AI coach review of a match")
def coach_match(match_id: MatchId, lang: str = "en"):
    detail = PLAYER_SERVICE.match_detail(match_id, normalize_lang(lang), force_coach=True)
    if detail is None:
        return JSONResponse(status_code=404, content={"status": "error", "code": "match_not_found"})
    return detail["coach"]


@router.post("/career/ask", summary="Ask the AI coach a question about the recent matches")
def ask_career(request: AskRequest, lang: str = "en"):
    return PLAYER_SERVICE.ask_career(request.question, normalize_lang(lang))


@router.post("/career/coach", summary="(Re)generate the AI coach review of recent matches")
def coach_career(lang: str = "en"):
    return PLAYER_SERVICE.career(normalize_lang(lang), force_coach=True).get("coach")


@router.get("/opendota", summary="OpenDota key status (the key is never returned)")
def opendota_settings():
    return PLAYER_SERVICE.opendota_status()


@router.post("/opendota", summary="Save an OpenDota API key")
def set_opendota_settings(request: OpenDotaKeyRequest):
    try:
        return PLAYER_SERVICE.set_opendota_key(request.api_key)
    except ValueError:
        return JSONResponse(
            status_code=400, content={"status": "error", "code": "bad_opendota_key"}
        )


@router.delete("/opendota", summary="Forget the OpenDota API key")
def clear_opendota_settings():
    return PLAYER_SERVICE.clear_opendota_key()


@router.get("/ai", summary="AI coach settings (the key is never returned)")
def ai_settings():
    return PLAYER_SERVICE.ai_status()


@router.post("/ai", summary="Save the AI coach provider and key")
def set_ai_settings(request: AIRequest):
    try:
        return PLAYER_SERVICE.set_ai(request.provider, request.api_key, request.model)
    except ValueError:
        return JSONResponse(status_code=400, content={"status": "error", "code": "bad_ai_settings"})


@router.delete("/ai", summary="Forget the AI coach key")
def clear_ai_settings():
    return PLAYER_SERVICE.clear_ai()


@router.post("/ai/check", summary="Validate the AI coach key with one small request")
def check_ai_settings():
    return PLAYER_SERVICE.check_ai()
