"""
player_api.py - HTTP endpoints for the linked player, matches and reviews.

GET    /player                   account, sync state, live match, last review
POST   /player/link              {"steam": "<Steam ID / Friend ID / profile link>"}
POST   /player/link-detected     link the account currently seen in GSI
DELETE /player                   forget the linked account (matches stay stored)
POST   /player/sync              pull profile + recent matches from OpenDota
GET    /player/matches           match table (newest first)
GET    /player/matches/{id}      one match: summary, scoreboard, post-match review
POST   /player/matches/{id}/refresh   fetch again / ask OpenDota to parse the replay
GET    /player/career            statistics and advice over the recent matches

All review texts follow `lang` (ru/en).
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.advice_i18n import normalize_lang
from app.config import OPENDOTA_API_KEY, OPENDOTA_API_URL, OPENDOTA_ENABLED, PLAYER_DATA_DIR
from app.opendota import OpenDotaClient
from app.player_service import PlayerService
from app.steam_ids import SteamIdError

PLAYER_SERVICE = PlayerService(
    PLAYER_DATA_DIR,
    client=OpenDotaClient(OPENDOTA_API_URL, api_key=OPENDOTA_API_KEY) if OPENDOTA_ENABLED else None,
)

router = APIRouter(prefix="/player", tags=["player"])


class LinkRequest(BaseModel):
    steam: str


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
def player_matches(limit: int = 50, offset: int = 0):
    limit = max(1, min(int(limit), 200))
    return PLAYER_SERVICE.list_matches(limit=limit, offset=max(0, int(offset)))


@router.get("/matches/{match_id}", summary="Post-match review")
def player_match(match_id: int, lang: str = "en"):
    detail = PLAYER_SERVICE.match_detail(match_id, normalize_lang(lang))
    if detail is None:
        return JSONResponse(status_code=404, content={"status": "error", "code": "match_not_found"})
    return detail


@router.post(
    "/matches/{match_id}/refresh", summary="Fetch the match again and request a replay parse"
)
def refresh_match(match_id: int):
    PLAYER_SERVICE.fetch_match(match_id, request_parse=True)
    return {"status": "queued", "opendota": PLAYER_SERVICE.client is not None}


@router.get("/career", summary="Statistics and advice over recent matches")
def player_career(lang: str = "en"):
    return PLAYER_SERVICE.career(normalize_lang(lang))
