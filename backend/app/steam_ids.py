"""
steam_ids.py - parse what a player pastes as "my Steam account".

Dota and OpenDota identify a player by the 32-bit account id ("Friend ID" in
the Dota client). Steam uses the 64-bit SteamID. Accepted inputs:

- 64-bit SteamID: 76561198012345678
- account id / Friend ID: 52079950
- profile URL: https://steamcommunity.com/profiles/76561198012345678
- OpenDota / Dotabuff / Stratz player URL: .../players/52079950
- Steam3 "[U:1:52079950]" and legacy "STEAM_0:0:26039975"

Vanity URLs (steamcommunity.com/id/<name>) need the Steam Web API, so they are
rejected with a hint to use the Friend ID instead.
"""

from __future__ import annotations

import re

STEAM64_BASE = 76561197960265728
_MAX_ACCOUNT_ID = 2**32 - 1

_PROFILE_URL = re.compile(r"steamcommunity\.com/profiles/(\d{17})", re.IGNORECASE)
_VANITY_URL = re.compile(r"steamcommunity\.com/id/([^/?#\s]+)", re.IGNORECASE)
_PLAYER_URL = re.compile(
    r"(?:opendota\.com|dotabuff\.com|stratz\.com)/players/(\d+)", re.IGNORECASE
)
_STEAM3 = re.compile(r"^\[?U:1:(\d+)\]?$", re.IGNORECASE)
_STEAM2 = re.compile(r"^STEAM_[0-5]:([01]):(\d+)$", re.IGNORECASE)


class SteamIdError(ValueError):
    """Input is not a Steam account. `code` is stable for the UI."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def account_id_from_steam64(steam64: int) -> int:
    return int(steam64) - STEAM64_BASE


def steam64_from_account_id(account_id: int) -> int:
    return int(account_id) + STEAM64_BASE


def parse_account_id(value: object) -> int:
    """Return the 32-bit account id for any supported input, or raise SteamIdError."""
    text = str(value or "").strip()
    if not text:
        raise SteamIdError("empty", "Enter a Steam ID, Friend ID or profile link.")

    vanity = _VANITY_URL.search(text)
    if vanity:
        raise SteamIdError(
            "vanity_url",
            "Custom profile links (steamcommunity.com/id/…) cannot be resolved offline. "
            "Use the Friend ID from your Dota profile or a /profiles/7656… link.",
        )

    for pattern in (_PROFILE_URL, _PLAYER_URL):
        match = pattern.search(text)
        if match:
            return _from_number(match.group(1))

    steam3 = _STEAM3.match(text)
    if steam3:
        return _validated(int(steam3.group(1)))

    steam2 = _STEAM2.match(text)
    if steam2:
        return _validated(int(steam2.group(2)) * 2 + int(steam2.group(1)))

    digits = text.replace(" ", "")
    if digits.isdigit():
        return _from_number(digits)

    raise SteamIdError("unrecognized", "This does not look like a Steam ID or profile link.")


def _from_number(digits: str) -> int:
    number = int(digits)
    if number >= STEAM64_BASE:
        return _validated(account_id_from_steam64(number))
    return _validated(number)


def _validated(account_id: int) -> int:
    if not 0 < account_id <= _MAX_ACCOUNT_ID:
        raise SteamIdError("out_of_range", "This number is not a valid Steam account.")
    return account_id
