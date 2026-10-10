"""The weekly meta post (scripts/news.py, scripts/build_news.py): numbers from
OpenDota's public hero statistics, the same lists on the site and in Telegram."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import news  # noqa: E402 - scripts/news.py


def _stats(rows):
    return [
        {
            "id": index + 1,
            "localized_name": name,
            "pub_pick_trend": [picks // 7] * 7,
            "pub_win_trend": [wins // 7] * 7,
        }
        for index, (name, picks, wins) in enumerate(rows)
    ]


def _rows(top_win=0.56):
    rows = [(f"Hero {i}", 7_000, 3_500) for i in range(60)]
    rows[0] = ("Pudge", 70_000, 35_000)
    rows[1] = ("Wraith King", 14_000, int(14_000 * top_win))
    rows[2] = ("Rare Pick", 700, 630)  # wins 90 % of a handful of games
    return rows


def test_a_post_keeps_each_heros_week_and_the_lists_follow_the_numbers():
    post = news.meta_post(_stats(_rows()), date(2026, 10, 12))
    assert post["date"] == "2026-10-12" and post["from"] == "2026-10-06"
    assert {hero["name"] for hero in post["heroes"]} >= {"Pudge", "Wraith King"}
    data = news.summary(post, None)
    assert data["win"][0]["name"] == "Wraith King"
    assert "Rare Pick" not in {row["name"] for row in data["win"]}  # under 2 % of matches
    assert data["pick"][0]["name"] == "Pudge"
    assert data["up"] == [] and data["down"] == []  # no earlier post to compare with
    with pytest.raises(ValueError):
        news.meta_post(_stats(_rows()[:10]), date(2026, 10, 12))  # a broken answer


def test_movers_against_the_previous_post():
    before = news.meta_post(_stats(_rows(0.50)), date(2026, 10, 5))
    after = news.meta_post(_stats(_rows(0.56)), date(2026, 10, 12))
    assert news.previous_of(after, [after, before]) is before
    data = news.summary(after, before)
    assert [row["name"] for row in data["up"]] == ["Wraith King"]
    assert data["up"][0]["change"] == pytest.approx(6.0, abs=0.1)
    assert data["down"] == []


def test_texts_in_both_languages_and_the_telegram_post():
    post = news.meta_post(_stats(_rows()), date(2026, 10, 12))
    data = news.summary(post, None)
    assert news.title(post, "uk") == "Мета тижня: 6–12 жовтня"
    assert news.title(post, "en") == "Meta of the week: 6–12 October"
    assert news.percent(0.551, "uk") == "55,1 %" and news.percent(0.551, "en") == "55.1%"
    assert news.points(-1.24, "uk") == "−1,2 п. п."
    text = news.telegram_meta(post, data)
    assert text.startswith("<b>Мета тижня: 6–12 жовтня</b>")
    assert "1. Wraith King — 56,0 % перемог" in text
    assert "1. Pudge — у " in text and "% матчів" in text
    assert "/news/2026-10-12-meta.html?ref=tg" in text
    page = news.post_main(post, data, "uk", {"Pudge": "pudge"}, "../")
    assert '<a href="../heroes/pudge.html">Pudge</a>' in page
    assert "t.me/share/url?" in page


def test_a_release_post_fits_one_message():
    notes = "## Що нового\n\n" + "\n".join(f"- **Пункт {i}.** " + "текст " * 80 for i in range(20))
    notes += "\n\n---\n\n**In English:**\n- English part"
    text = news.telegram_release("0.55.0", notes)
    assert text.startswith("<b>Wardly 0.55.0</b>")
    assert "English part" not in text and len(text) < 4096
    assert text.endswith("Завантажити: https://luhovyimvp.dev/?ref=tg")
