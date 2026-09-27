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
