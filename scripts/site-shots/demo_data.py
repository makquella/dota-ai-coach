"""Demo data for the website screenshots: varied matches and a scripted AI coach."""

from __future__ import annotations

import json
import random
from typing import Any

from match_fixtures import opendota_match

UK = {
    "summary": "Матч вирішила лінія. На 10:00 у вас 36 добивань проти 65 в Anti-Mage. Дві смерті від Shadow Fiend (4:00 і 7:00) віддали йому темп, а далі відставання зростало: з 15:00 до 22:00 майже немає фарму, і Maelstrom прийшов на 26:00 замість звичних 20:00.",
    "turning_points": [
        {
            "time": "4:00",
            "text": "Перша смерть від Shadow Fiend: лінія стала небезпечною, добивання просіли.",
        },
        {
            "time": "15:00",
            "text": "Почався провал у фармі до 22:00: золото майже не росло, а вороги забрали центр мапи.",
        },
        {
            "time": "26:00",
            "text": "Maelstrom на 6 хвилин пізніше звичного: з таким таймінгом герой виграє 40% ігор замість 50%.",
        },
    ],
    "mistakes": [
        {
            "title": "Лінія проти Shadow Fiend і Anti-Mage",
            "detail": "Дві смерті на лінії віддали темп. На 10:00 у вас 36 добивань, а добрий темп для керрі — помітно більший.",
            "fix": "Проти Shadow Fiend стійте за кріпами й відходьте, коли він підходить на удар. Якщо лінію програно, раніше йдіть у ліс: збережете і добивання, і життя.",
        },
    ],
    "strengths": [],
    "next_game": ["Maelstrom до 20:00.", "Не більше 2 смертей на лінії."],
}
EN = {
    "summary": "The lane decided the match. By 10:00 you had 36 last hits against 65 for Anti-Mage. Two deaths to Shadow Fiend (4:00 and 7:00) handed him the tempo, and then the gap grew: almost no farm from 15:00 to 22:00, and Maelstrom came at 26:00 instead of the usual 20:00.",
    "turning_points": [
        {
            "time": "4:00",
            "text": "First death to Shadow Fiend: the lane became dangerous and last hits dropped.",
        },
        {
            "time": "15:00",
            "text": "A farm gap until 22:00: gold barely grew while the enemies took the middle of the map.",
        },
        {
            "time": "26:00",
            "text": "Maelstrom 6 minutes later than usual: with that timing the hero wins 40% of games instead of 50%.",
        },
    ],
    "mistakes": [
        {
            "title": "The lane against Shadow Fiend and Anti-Mage",
            "detail": "Two lane deaths handed over the tempo. By 10:00 you had 36 last hits, well below a good carry pace.",
            "fix": "Against Shadow Fiend stay behind your creeps and step back when he walks up to hit. If the lane is lost, go to the jungle earlier: keep both the last hits and your life.",
        },
    ],
    "strengths": [],
    "next_game": ["Maelstrom by 20:00.", "No more than 2 lane deaths."],
}

CAREER_UK = {
    "summary": "Juggernaut — ваш основний герой, і на ньому ви виграєте найчастіше. Головна проблема — серії смертей: після першої смерті наступні йдуть одна за одною.",
    "patterns": [
        {
            "title": "Серії смертей",
            "detail": "Смерті йдуть поспіль після першої помилки.",
            "fix": "Після смерті спершу погляньте на мапу, потім обирайте маршрут.",
        },
    ],
    "strengths": ["Добра лінія в переможних матчах."],
    "plan": ["Не більше 5 смертей за матч.", "Перший предмет до 15:00."],
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
        uk = "Write in Ukrainian" in system
        if "patterns" in system:  # noqa: SIM108 - match vs career reads clearer
            answer = CAREER_UK if uk else CAREER_EN
        else:
            answer = UK if uk else EN
        return json.dumps(answer, ensure_ascii=False)

    def check(self) -> None:
        pass


# Mostly Juggernaut (the "same hero" numbers need games), some other carries.
POOL = [8, 8, 8, 8, 44, 8, 109, 8, 67, 8, 41, 8, 94, 8, 18, 8, 12, 8, 44, 8]
# The final inventory of a won / a lost game per hero (the match table's icons).
INVENTORIES = {
    8: (
        ["phase_boots", "bfury", "manta", "black_king_bar", "abyssal_blade", "butterfly"],
        ["phase_boots", "maelstrom", "wraith_band", "magic_wand", "yasha"],
    ),
    44: (
        ["phase_boots", "bfury", "desolator", "black_king_bar", "satanic", "abyssal_blade"],
        ["power_treads", "bfury", "magic_wand", "wraith_band"],
    ),
    109: (
        ["power_treads", "manta", "skadi", "black_king_bar", "butterfly", "satanic"],
        ["power_treads", "dragon_lance", "yasha", "wraith_band", "magic_wand"],
    ),
    67: (
        ["power_treads", "radiance", "manta", "diffusal_blade", "skadi", "heart"],
        ["power_treads", "radiance", "magic_wand", "wraith_band"],
    ),
    41: (
        ["power_treads", "maelstrom", "black_king_bar", "butterfly", "satanic", "mjollnir"],
        ["power_treads", "maelstrom", "magic_wand", "wraith_band"],
    ),
    94: (
        ["power_treads", "manta", "skadi", "butterfly", "greater_crit", "black_king_bar"],
        ["power_treads", "dragon_lance", "manta", "magic_wand"],
    ),
    18: (
        ["power_treads", "echo_sabre", "black_king_bar", "greater_crit", "satanic", "assault"],
        ["power_treads", "echo_sabre", "magic_wand", "bracer"],
    ),
    12: (
        ["power_treads", "diffusal_blade", "manta", "heart", "butterfly", "skadi"],
        ["power_treads", "diffusal_blade", "magic_wand", "wraith_band"],
    ),
}


# The other nine players of the fixture's lineup (the scoreboard's icons).
LINEUP_ITEMS = {
    74: [
        "hand_of_midas",
        "travel_boots",
        "ultimate_scepter",
        "octarine_core",
        "black_king_bar",
        "blink",
    ],
    129: ["phase_boots", "blink", "black_king_bar", "desolator", "assault", "magic_wand"],
    26: ["tranquil_boots", "blink", "aether_lens", "force_staff", "ghost", "magic_wand"],
    5: ["tranquil_boots", "glimmer_cape", "force_staff", "blink", "ward_observer", "magic_wand"],
    1: ["power_treads", "bfury", "manta", "abyssal_blade", "butterfly", "skadi"],
    11: ["power_treads", "black_king_bar", "desolator", "satanic", "blink", "ultimate_scepter"],
    2: ["phase_boots", "blink", "blade_mail", "black_king_bar", "heart", "magic_wand"],
    86: ["arcane_boots", "blink", "aether_lens", "force_staff", "glimmer_cape", "magic_wand"],
    30: [
        "arcane_boots",
        "glimmer_cape",
        "ultimate_scepter",
        "force_staff",
        "magic_wand",
        "ward_observer",
    ],
}


def _inventory(me: dict[str, Any], hero: int, good: bool) -> None:
    """item_0 … item_5 of the hero's usual game (strings: the fixtures' items)."""
    won, lost = INVENTORIES.get(hero, INVENTORIES[8])
    for slot, key in enumerate(won if good else lost):
        me[f"item_{slot}"] = key


def _lineup_items(match: dict[str, Any]) -> None:
    for player in match["players"][1:]:
        for slot, key in enumerate(LINEUP_ITEMS.get(player.get("hero_id"), [])):
            player[f"item_{slot}"] = key


TOTALS = ("last_hits", "net_worth", "hero_damage", "tower_damage")


# How pro players level Juggernaut (real OpenDota ability ids and names), for the
# review's skill card and the live skill tip.
_FURY, _WARD, _DANCE, _OMNI = (
    "juggernaut_blade_fury",
    "juggernaut_healing_ward",
    "juggernaut_blade_dance",
    "juggernaut_omni_slash",
)
_PRO_GAME = [
    _FURY,
    _DANCE,
    _FURY,
    _DANCE,
    _FURY,
    _OMNI,
    _FURY,
    _DANCE,
    _DANCE,
    "special_bonus_unique_juggernaut_3",
    _WARD,
    _OMNI,
    _WARD,
    _WARD,
    _WARD,
]
PRO_SKILLS = {
    "orders": [_PRO_GAME] * 5,
    "names": {
        _FURY: "Blade Fury",
        _WARD: "Healing Ward",
        _DANCE: "Blade Dance",
        _OMNI: "Omnislash",
        "special_bonus_unique_juggernaut_3": "-1.0s Bladeform Stack Gain Interval",
    },
    "ids": {
        "5027": _DANCE,
        "5028": _FURY,
        "5029": _WARD,
        "5030": _OMNI,
        "7021": "special_bonus_unique_juggernaut_3",
    },
    "talents": {"special_bonus_unique_juggernaut_3": 10},
}


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
            # Healing Ward maxed first (the pros start with Blade Fury: PRO_SKILLS).
            me["ability_upgrades_arr"] = [
                5029,
                5028,
                5029,
                5027,
                5029,
                5030,
                5029,
                5028,
                5028,
                7021,
                5028,
                5030,
                5027,
                5027,
                5027,
                730,
                5030,
            ]
            me["lane_pos"] = {
                str(x): {str(y): 4 + (x * 7 + y * 3) % 23 for y in range(74, 86, 2)}
                for x in range(150, 176, 2)
            }
            match["start_time"] = row["start_time"]
            _inventory(me, 8, good)
            _lineup_items(match)
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
        _inventory(me, hero, good)
        _lineup_items(match)
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
    [
        (-60, *FOUNTAIN),
        (-30, -5600, -6500),
        (0, -3200, -6450),
        (40, 900, -6350),
        (90, 2300, -6200),
        (130, 1500, -6300),
        (180, 2600, -6150),
        (225, 1900, -6250),
        (240, 2300, -6150),
    ],
    [
        (260, *FOUNTAIN),
        (300, -3500, -6450),
        (340, 1200, -6350),
        (380, 2900, -6150),
        (420, 3700, -6000),
    ],
    [
        (440, *FOUNTAIN),
        (480, -3600, -6450),
        (520, 800, -6350),
        (560, 2400, -6200),
        (600, 1400, -6300),
        (650, 300, -5000),
        (700, -900, -4100),
        (760, -2300, -3300),
        (820, -3100, -4500),
        (880, -1600, -5200),
        (930, -300, -4000),
        (990, -700, -2600),
        (1040, 700, -1900),
        (1100, 1600, -900),
        (1150, 2100, 300),
        (1210, 3100, 900),
        (1260, 3100, 1900),
        (1300, 3600, 1300),
    ],
    [
        (1320, *FOUNTAIN),
        (1360, -4600, -4700),
        (1400, -2600, -2700),
        (1440, -1300, -1400),
        (1470, 200, 800),
        (1500, 1300, 3400),
    ],
    [
        (1520, *FOUNTAIN),
        (1560, -3500, -6400),
        (1610, 1500, -6300),
        (1680, 4800, -6150),
        (1740, 6200, -5200),
        (1800, 6300, -3300),
        (1860, 4900, -2900),
        (1920, 3900, -4100),
        (1990, 2600, -3600),
        (2050, 2300, -2700),
        (2100, 2750, -2300),
    ],
    [
        (2120, *FOUNTAIN),
        (2160, -3500, -6400),
        (2200, 2600, -6250),
        (2230, 6000, -5600),
        (2250, 6300, 1400),
    ],
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
