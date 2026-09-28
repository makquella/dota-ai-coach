"""
role_analysis.py - what a mid and a support are judged by beyond farm and fights.

Parsed replays only (OpenDota counts runes, stacks and wards from the replay):

- mid: power / bounty / wisdom runes picked up (rune_pickups) per 10 minutes and
  against the enemy mid of the same match (player_roles); runes are the mid's
  tempo, so the findings sit in the laning section;
- support: camps stacked and sentry wards over the whole game (a support with
  no sentries cannot answer invisible heroes or dewarding).

Returns (block, findings): the block is stored as analysis["role_play"] and shown
in the review's laning / vision facts; the findings use _finding's shape.
"""

from __future__ import annotations

from typing import Any

from app.peer_analysis import player_roles

RUNES_GOOD_PER_10 = 3.0
RUNES_LOW_PER_10 = 1.5
RUNES_BEHIND_BY = 4
MIN_MINUTES = 20
STACKS_LOW_MAX = 1
STACKS_MIN_MINUTES = 25


def _finding(
    finding_id: str, kind: str, section: str, severity: int = 1, weight: float = 1.0, **params
):
    return {
        "id": finding_id,
        "kind": kind,
        "section": section,
        "severity": severity,
        "weight": weight,
        "params": params,
    }


def _enemy_mid_runes(opendota: dict[str, Any] | None) -> tuple[str | None, int | None]:
    if not opendota:
        return None, None
    players = opendota.get("players") or []
    me = next((p for p in players if p.get("me")), None)
    if me is None:
        return None, None
    roles = player_roles(players, opendota.get("duration"))
    my_side = bool(me.get("isRadiant", True))
    for player, role in zip(players, roles, strict=True):
        if role == "mid" and bool(player.get("isRadiant", True)) != my_side:
            runes = player.get("rune_pickups")
            return player.get("hero"), int(runes) if isinstance(runes, (int, float)) else None
    return None, None


def analyze_role(
    facts: dict[str, Any], opendota: dict[str, Any] | None, position: str | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    minutes = (facts.get("duration") or 0) / 60
    if not facts.get("parsed") or minutes < MIN_MINUTES or position not in ("mid", "support"):
        return None, []
    findings: list[dict[str, Any]] = []
    if position == "mid":
        runes = facts.get("rune_pickups")
        if not isinstance(runes, int):
            return None, []
        per10 = round(runes / (minutes / 10), 1)
        enemy_hero, enemy_runes = _enemy_mid_runes(opendota)
        block: dict[str, Any] = {"runes": runes, "runes_per_10": per10}
        if enemy_runes is not None:
            block.update(enemy_mid=enemy_hero, enemy_runes=enemy_runes)
        if enemy_runes is not None and enemy_runes >= runes + RUNES_BEHIND_BY:
            findings.append(
                _finding(
                    "runes_behind",
                    "improve",
                    "laning",
                    severity=2,
                    weight=1.3,
                    runes=runes,
                    enemy_runes=enemy_runes,
                    hero=enemy_hero,
                )
            )
        elif per10 < RUNES_LOW_PER_10:
            findings.append(
                _finding(
                    "runes_low",
                    "improve",
                    "laning",
                    severity=1,
                    runes=runes,
                    minutes=round(minutes),
                )
            )
        elif per10 >= RUNES_GOOD_PER_10 and (enemy_runes is None or runes > enemy_runes):
            findings.append(_finding("runes_good", "strength", "laning", weight=1.2, runes=runes))
        return block, findings

    stacks, sentries = facts.get("camps_stacked"), facts.get("sen_placed")
    block = {"camps_stacked": stacks, "sen_placed": sentries}
    if isinstance(stacks, int) and stacks <= STACKS_LOW_MAX and minutes >= STACKS_MIN_MINUTES:
        findings.append(
            _finding("stacks_low", "improve", "vision", stacks=stacks, minutes=round(minutes))
        )
    if sentries == 0:
        findings.append(
            _finding("sentries_none", "improve", "vision", weight=1.2, minutes=round(minutes))
        )
    return block, findings
