"""Demo data for the website screenshots: varied matches and a scripted AI coach."""

from __future__ import annotations

import json
import random
from typing import Any

from match_fixtures import opendota_match

RU = {
    "summary": "Матч проигран на линии: к 10:00 у вас 36 добиваний против 65 у Anti-Mage, а две смерти от Shadow Fiend (4:00 и 7:00) отдали ему темп. Дальше отставание росло: с 15:00 по 22:00 почти нет фарма, и Maelstrom пришёл к 26:00 вместо обычных 20:00.",
    "turning_points": [
        {
            "time": "4:00",
            "text": "Первая смерть от Shadow Fiend: линия стала опасной, добивания просели.",
        },
        {
            "time": "15:00",
            "text": "Начался провал в фарме до 22:00: за это время всего 3 добивания.",
        },
        {
            "time": "26:00",
            "text": "Maelstrom на 6 минут позже обычного: с таким таймингом герой выигрывает 40% игр вместо 50%.",
        },
    ],
    "mistakes": [
        {
            "title": "Линия против Shadow Fiend и Anti-Mage",
            "detail": "Две смерти на линии и 36 добиваний к 10:00 при хорошем темпе 55. Anti-Mage за то же время добил 65.",
            "fix": "Против Shadow Fiend стойте за крипами и отходите, когда он подходит на удар. Если линия проиграна, раньше уходите в лес: сохраните и добивания, и жизнь.",
        },
    ],
    "strengths": [],
    "next_game": ["Maelstrom к 20:00.", "Не больше 2 смертей на линии."],
}
EN = {
    "summary": "The lane decided the match: 36 last hits by 10:00 against 65 for Anti-Mage, and two deaths to Shadow Fiend (4:00 and 7:00) handed him the tempo. Then the gap grew: almost no farm from 15:00 to 22:00, and Maelstrom came at 26:00 instead of the usual 20:00.",
    "turning_points": [
        {
            "time": "4:00",
            "text": "First death to Shadow Fiend: the lane became dangerous and last hits dropped.",
        },
        {
            "time": "15:00",
            "text": "A farm gap until 22:00: only 3 last hits in that time.",
        },
        {
            "time": "26:00",
            "text": "Maelstrom 6 minutes later than usual: with that timing the hero wins 40% of games instead of 50%.",
        },
    ],
    "mistakes": [
        {
            "title": "The lane against Shadow Fiend and Anti-Mage",
            "detail": "Two lane deaths and 36 last hits by 10:00 where a good pace is 55. Anti-Mage had 65 by then.",
            "fix": "Against Shadow Fiend stay behind your creeps and step back when he walks up to hit. If the lane is lost, go to the jungle earlier: keep both the last hits and your life.",
        },
    ],
    "strengths": [],
    "next_game": ["Maelstrom by 20:00.", "No more than 2 lane deaths."],
}

CAREER_RU = {
    "summary": "Juggernaut — ваш основной герой, и на нём вы выигрываете чаще всего. Главная проблема — серии смертей: после первой смерти следующие идут одна за другой.",
    "patterns": [
        {
            "title": "Серии смертей",
            "detail": "Смерти идут подряд после первой ошибки.",
            "fix": "После смерти сначала посмотрите на карту, потом выбирайте маршрут.",
        },
    ],
    "strengths": ["Хорошая линия в победных матчах."],
    "plan": ["Не больше 5 смертей за матч.", "Первый предмет к 15:00."],
}
CAREER_EN = {
    "summary": "Juggernaut is your main hero and the one you win on most. The main problem is death streaks: after the first death the next ones come one after another.",
    "patterns": [
        {
            "title": "Death streaks",
            "detail": "Deaths come in a row after the first mistake.",
            "fix": "After a death look at the map first, then pick your route.",
        },
    ],
    "strengths": ["A good lane in the games you win."],
    "plan": ["No more than 5 deaths per match.", "First item by 15:00."],
}


class DemoLLM:
    """Stands in for the AI coach: a fixed review per language (match or career)."""

    label = {"provider": "gemini", "model": "gemini-3.8-flash"}

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        system = messages[0]["content"]
        ru = "Write in Russian" in system
        if "patterns" in system:
            answer = CAREER_RU if ru else CAREER_EN
        else:
            answer = RU if ru else EN
        return json.dumps(answer, ensure_ascii=False)

    def check(self) -> None:
        pass


# Mostly Juggernaut (the "same hero" numbers need games), some other carries.
POOL = [8, 8, 8, 8, 44, 8, 109, 8, 67, 8, 41, 8, 94, 8, 18, 8, 12, 8, 44, 8]
TOTALS = ("last_hits", "net_worth", "hero_damage", "tower_damage")


def vary(recent: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """OpenDota matches for `recent` (edited in place to match): the first one stays
    the fixture the scripted AI review describes, the rest get other heroes,
    durations, deaths and numbers."""
    rnd = random.Random(7)
    matches: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(recent):
        good = row["radiant_win"]
        if index == 0:
            match = opendota_match(good=good, match_id=row["match_id"])
            me = match["players"][0]
            # A parsed replay's wards and laning position, for the match map.
            me["obs_log"] = [
                {"time": 130, "x": 118, "y": 112},
                {"time": 900, "x": 150, "y": 96},
                {"time": 1500, "x": 104, "y": 140},
            ]
            me["sen_log"] = [{"time": 610, "x": 131, "y": 118}]
            me["lane_pos"] = {
                str(x): {str(y): 4 + (x * 7 + y * 3) % 23 for y in range(74, 86, 2)}
                for x in range(150, 176, 2)
            }
            match["start_time"] = row["start_time"]
            matches[row["match_id"]] = match
            row.update(hero_id=8)
            continue
        duration = rnd.randrange(28, 52) * 60
        n_deaths = rnd.randint(1, 5) if good else rnd.randint(5, 10)
        deaths = sorted(rnd.sample(range(200, duration - 60, 37), n_deaths))
        match = opendota_match(
            good=good, match_id=row["match_id"], duration=duration, my_deaths=deaths
        )
        me = match["players"][0]
        factor = rnd.uniform(0.78, 1.15)
        hero = POOL[index % len(POOL)]
        me["hero_id"] = hero
        me["kills"] = max(0, round(me["kills"] * rnd.uniform(0.5, 1.4)))
        me["assists"] = max(0, round(me["assists"] * rnd.uniform(0.6, 1.4)))
        for key in ("gold_per_min", "xp_per_min", *TOTALS):
            scale = factor * duration / (38 * 60) if key in TOTALS else factor
            me[key] = int(round(me[key] * scale))
        for key in ("lh_t", "gold_t", "xp_t"):
            if key in me:
                me[key] = [int(v * factor) for v in me[key]]
        match["start_time"] = row["start_time"]
        matches[row["match_id"]] = match
        row.update(
            hero_id=hero,
            duration=duration,
            kills=me["kills"],
            deaths=me["deaths"],
            assists=me["assists"],
            gold_per_min=me["gold_per_min"],
            xp_per_min=me["xp_per_min"],
            last_hits=me["last_hits"],
        )
    return matches


# --- the recorded match on the map --------------------------------------------------
# A believable game of a Radiant safe-lane Juggernaut (live GSI world coordinates:
# centre 0, Radiant bottom-left): two lane deaths to Shadow Fiend, then farm, and
# deaths in the Dire jungle, at Roshan and at a Dire tower. The death times are those
# of the parsed replay (opendota_match's defaults), so every death gets its place.
FOUNTAIN = (-7000, -6700)
RESPAWN = 20
ROUTE_DEATHS = (240, 420, 1300, 1500, 2100, 2250)
# (clock, x, y) waypoints of each life; the hero walks straight between them.
LIVES: list[list[tuple[int, int, int]]] = [
    [(-60, *FOUNTAIN), (-30, -5600, -6500), (0, -3200, -6450), (40, 900, -6350),
     (90, 2300, -6200), (130, 1500, -6300), (180, 2600, -6150), (225, 1900, -6250),
     (240, 2300, -6150)],
    [(260, *FOUNTAIN), (300, -3500, -6450), (340, 1200, -6350), (380, 2900, -6150),
     (420, 3700, -6000)],
    [(440, *FOUNTAIN), (480, -3600, -6450), (520, 800, -6350), (560, 2400, -6200),
     (600, 1400, -6300), (650, 300, -5000), (700, -900, -4100), (760, -2300, -3300),
     (820, -3100, -4500), (880, -1600, -5200), (930, -300, -4000), (990, -700, -2600),
     (1040, 700, -1900), (1100, 1600, -900), (1150, 2100, 300), (1210, 3100, 900),
     (1260, 3100, 1900), (1300, 3600, 1300)],
    [(1320, *FOUNTAIN), (1360, -4600, -4700), (1400, -2600, -2700), (1440, -1300, -1400),
     (1470, 200, 800), (1500, 1300, 3400)],
    [(1520, *FOUNTAIN), (1560, -3500, -6400), (1610, 1500, -6300), (1680, 4800, -6150),
     (1740, 6200, -5200), (1800, 6300, -3300), (1860, 4900, -2900), (1920, 3900, -4100),
     (1990, 2600, -3600), (2050, 2300, -2700), (2100, 2750, -2300)],
    [(2120, *FOUNTAIN), (2160, -3500, -6400), (2200, 2600, -6250), (2230, 6000, -5600),
     (2250, 6300, 1400)],
    [(2270, *FOUNTAIN), (2280, *FOUNTAIN)],
]


def route_position(t: int) -> tuple[int, int] | None:
    """Where the hero stands at clock `t`; None while dead."""
    for life in LIVES:
        if life[0][0] <= t <= life[-1][0]:
            for (t0, x0, y0), (t1, x1, y1) in zip(life, life[1:], strict=False):
                if t0 <= t <= t1:
                    k = (t - t0) / (t1 - t0) if t1 > t0 else 0
                    return round(x0 + (x1 - x0) * k), round(y0 + (y1 - y0) * k)
    return None


def with_route(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """gsi_match_stream payloads (no deaths of their own) moved along LIVES."""
    for payload in payloads:
        t = payload["map"]["clock_time"]
        deaths = sum(1 for d in ROUTE_DEATHS if d <= t)
        payload["player"]["deaths"] = deaths
        position = route_position(t)
        hero = payload["hero"]
        dead = position is None or any(d <= t < d + RESPAWN for d in ROUTE_DEATHS)
        hero.update(alive=not dead, health_percent=0 if dead else 80)
        hero["respawn_seconds"] = RESPAWN if dead else 0
        if dead:
            payload["player"]["gold"] = 900
        else:
            hero.update(xpos=position[0], ypos=position[1])
    return payloads


# --- the friend on the Progress page ------------------------------------------------
FRIEND_HEROES = [11, 8, 17, 11, 106, 8, 11, 74, 17, 11]


def friend_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    """One of the player's summaries turned into the friend's game."""
    friend = dict(row)
    friend["match_id"] = 9_100_000 + index
    friend["hero_id"] = FRIEND_HEROES[index % len(FRIEND_HEROES)]
    friend["win"] = index % 5 in (0, 2)
    for key, factor in (("gpm", 0.9), ("xpm", 1.04), ("last_hits", 0.86), ("hero_damage", 1.3)):
        if isinstance(friend.get(key), (int, float)):
            friend[key] = int(friend[key] * factor)
    friend["deaths"] = (friend.get("deaths") or 0) + 2
    friend["kills"] = (friend.get("kills") or 0) + 3
    return friend
