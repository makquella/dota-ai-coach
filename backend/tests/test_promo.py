"""Wardly Marketing Engine (scripts/promo): scripts built from the data, the
topic rotation, the quality gate, the frame timeline and the approval message.
The video render itself needs Chrome and ffmpeg and is not run here."""

from __future__ import annotations

import json
import random
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.promo import pronounce, quality, scenes, script, send, topics  # noqa: E402


def _week():
    heroes = [
        ("Wraith King", "skeleton_king", 14_000, 7_840),
        ("Outworld Devourer", "obsidian_destroyer", 13_000, 6_890),
        ("Spectre", "spectre", 12_000, 6_360),
        ("Pudge", "pudge", 70_000, 33_000),
    ] + [(f"Hero {i}", f"hero_{i}", 7_000, 3_500) for i in range(30)]
    post = {
        "date": "2026-10-12",
        "heroes": [{"name": n, "key": k, "picks": p, "wins": w} for n, k, p, w in heroes],
    }
    matches = sum(h["picks"] for h in post["heroes"]) / 10
    rows = [
        {
            "name": h["name"],
            "key": h["key"],
            "win": h["wins"] / h["picks"],
            "pick": h["picks"] / matches,
        }
        for h in post["heroes"]
    ]
    data = {
        "matches": matches,
        "win": sorted(rows, key=lambda r: r["win"], reverse=True),
        "pick": sorted(rows, key=lambda r: r["pick"], reverse=True),
        "up": [{**rows[2], "change": 1.48}],
        "down": [],
    }
    return post, data


def _hero(key="antimage", name="Anti-Mage"):
    return {
        "name": name,
        "slug": key.replace("_", "-"),
        "key": key,
        "position": "carry",
        "profile": {"low_hp_warning_threshold": 50, "critical_hp_threshold": 35},
    }


def test_the_voice_says_dota_names_and_agrees_percent_words():
    text, guessed = pronounce.for_voice(
        "Terrorblade виграє 53 %, а Black King Bar рятує. Glimpse 21 % і 55,1 %."
    )
    assert "Терорблейд" in text and "бі-кей-бі" in text
    assert "53 відсотки" in text and "21 відсоток" in text and "55,1 відсотка" in text
    assert guessed == ["Glimpse"]  # read by the rules: the quality report lists it
    assert not any("a" <= ch.lower() <= "z" for ch in text)


def test_the_meta_video_names_the_three_best_with_their_numbers():
    post, data = _week()
    item = script.meta(post, data, "6–12 жовтня", random.Random(1))
    rows = item.scenes[1].data["rows"]
    assert [r["name"] for r in rows] == ["Wraith King", "Outworld Devourer", "Spectre"]
    assert rows[0]["value"] == "56,0 %"
    assert "56 відсотків перемог" in item.scenes[1].voice
    assert "data/news/posts/2026-10-12-meta.json" in item.sources[0]
    assert item.caption.endswith("#spectre") and "?ref=promo-meta" in item.caption


def test_a_fact_only_when_the_number_is_surprising():
    post, data = _week()
    item = script.fact(post, data, "6–12 жовтня")
    assert item is not None and "Pudge" in item.title and "програє" in item.title  # 47 % of wins
    data["pick"][0] = {**data["pick"][0], "win": 0.51}
    assert script.fact(post, data, "6–12 жовтня") is None


def test_hero_tips_are_always_three_and_numbered_in_order():
    facts = {
        "role": "Саппорт",
        "archetype": "саппорт",
        "low": "60",
        "saves": "",
        "fight": "Hex",
        "pace": "5–15",
        "note": "Тримай дистанцію.",
    }
    item = script.hero_tips(_hero("shadow_shaman", "Shadow Shaman"), facts, random.Random(2))
    tips = item.scenes[1].data["tips"]
    assert len(tips) == 3
    assert [t["voice"].split(".")[0] for t in tips] == ["Перше", "Друге", "Третє"]
    assert tips[0]["text"] == "Відходь, коли HP нижче 60 %"
    with pytest.raises(ValueError):
        script.hero_tips(_hero(), {**facts, "fight": "", "pace": "", "note": ""}, random.Random(2))


def test_the_coach_video_shows_the_cards_the_app_showed():
    cards = [
        {
            "moment": "fall",
            "mode": "urgent",
            "action": "Використайте Blink зараз.",
            "reason": "За 5 секунд пішло 36% HP.",
        },
        {
            "moment": "stun",
            "mode": "urgent",
            "action": "Щойно контроль закінчиться, натисніть BKB.",
            "reason": "",
        },
    ]
    item = script.coach(_hero(), cards, random.Random(3), "0.56.2")
    kinds = [s.kind for s in item.scenes]
    assert kinds == ["hook", "card", "card", "stat", "cta"]
    assert item.scenes[1].data["action"] == cards[0]["action"]
    assert "0.56.2" in item.sources[0]
    with pytest.raises(ValueError):
        script.coach(_hero(), [], random.Random(3), "0.56.2")


def test_the_topic_rotation(monkeypatch):
    post, _ = _week()
    heroes = [_hero(f"hero_{i}", f"Hero {i}") for i in range(30)]
    monkeypatch.setattr(
        topics, "latest_release", lambda today: ("0.56.2", "## Що нового\n- **Пункт.** Текст")
    )
    today = date(2026, 10, 13)
    assert topics.choose(today, heroes, post, [], weights=topics.WEIGHTS).format == "release"
    done = [{"format": "release", "topic": "0.56.2"}]
    choice = topics.choose(today, heroes, post, done, weights=topics.WEIGHTS)
    assert choice.format != "release"
    # Never the same format twice in a row; the same day picks the same.
    for last in ("coach", "hero", "meta"):
        history = [*done, {"format": last, "topic": "x"}]
        first = topics.choose(today, heroes, post, history, weights=topics.WEIGHTS)
        assert first.format != last
        assert (
            topics.choose(today, heroes, post, history, weights=topics.WEIGHTS).topic == first.topic
        )
    # Recent heroes wait their turn.
    recent = [{"format": "coach", "topic": f"hero_{i}"} for i in range(topics.HERO_REPEAT)]
    fresh = {f"hero_{i}" for i in range(topics.HERO_REPEAT, 30)}
    assert topics.choose(today, heroes, post, recent, forced="coach").topic in fresh
    with pytest.raises(SystemExit):
        topics.choose(
            today, heroes, post, [{"format": "meta", "topic": "2026-10-12"}], forced="meta"
        )


def test_learned_weights_are_bounded(tmp_path, monkeypatch):
    path = tmp_path / "weights.json"
    path.write_text(json.dumps({"multipliers": {"coach": 50, "meta": 0.01, "spam": 9}}))
    monkeypatch.setattr(topics, "WEIGHTS_FILE", path)
    weights = topics.load_weights()
    assert weights["coach"] == topics.WEIGHTS["coach"] * topics.MAX_WEIGHT
    assert weights["meta"] == topics.WEIGHTS["meta"] * topics.MIN_WEIGHT
    assert "spam" not in weights


def _package(**changes):
    post, data = _week()
    item = script.meta(post, data, "6–12 жовтня", random.Random(1))
    package = {
        "id": "0123456789abcdef",
        "format": item.format,
        "topic": item.topic,
        "hook": item.hook,
        "title": item.title,
        "youtube_title": script.youtube_title(item),
        "caption": item.caption,
        "telegram_caption": item.caption[:1024],
        "seconds": 30.0,
        "voice": "piper",
        "script": item.to_dict(),
        "pronunciation_guesses": [],
    }
    return {**package, **changes}


def test_the_quality_gate():
    media = {"seconds": 31.0, "width": 1080, "height": 1920, "audio": True, "bytes": 9_000_000}
    assert quality.check(_package(), media)["ok"]
    assert not quality.check(_package(), {**media, "seconds": 75})["ok"]
    assert not quality.check(_package(), {**media, "height": 1080})["ok"]
    silent = {**media, "audio": False}
    assert not quality.check(_package(), silent)["ok"]
    assert quality.check(_package(), silent, allow_silent=True)["ok"]
    assert not quality.check(_package(caption="Гарантовано +1000 MMR"), media)["ok"]
    assert not quality.check(_package(caption="Герой {name}"), media)["ok"]
    report = quality.check(_package(pronunciation_guesses=["Glimpse"]), media)
    assert report["ok"] and "Glimpse" in report["warnings"][0]


def test_the_timeline_follows_the_voice_and_keeps_the_hook_clean():
    raw = [
        {"kind": "hook", "voice": "Хто тягне ігри цього тижня?", "data": {}},
        {
            "kind": "stat",
            "voice": "Найбільше виріс Spectre: плюс 1,5 пункту за тиждень.",
            "data": {"value": "+1,5", "label": "x"},
        },
        {"kind": "cta", "voice": "Wardly безкоштовний.", "data": {}},
    ]
    line = scenes.timeline(raw, [2.0, 3.5, None])
    assert line[0]["subs"] == []  # the headline is the voice
    assert line[1]["start"] == line[0]["end"] and line[1]["end"] - line[1][
        "start"
    ] == pytest.approx(3.5 + scenes.SCENE_PAD)
    assert line[1]["subs"][-1]["end"] <= line[1]["start"] + 3.5 + 1e-6
    assert all(len(s["text"]) <= scenes.SUB_CHARS + 12 for s in line[1]["subs"])
    page = scenes.page("meta", line, {}, 0)
    assert page.count('class="scene scene-') == 3 and "window.renderAt" in page
    assert "Мета тижня" in page  # the pill


def test_the_approval_message_fits_and_the_buttons_name_the_package(monkeypatch, tmp_path, capsys):
    package = _package(quality={"ok": True, "errors": [], "warnings": ["вимова: Glimpse"]})
    assert len(send.approval_caption(package)) <= 1024
    buttons = [b for row in send.keyboard(package["id"])["inline_keyboard"] for b in row]
    assert {b["callback_data"] for b in buttons} == {
        f"promo:{a}:{package['id']}" for a in ("all", "tg", "no")
    }
    assert all(len(b["callback_data"].encode()) <= 64 for b in buttons)
    (tmp_path / "video.mp4").write_bytes(b"\x00" * 10)
    sent = []

    class Answer:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return self.body

    def urlopen(request, timeout):
        sent.append(request)
        if request.full_url.endswith("/v1/admin/promo"):
            return Answer(b'{"ok": true, "media_key": "' + b"a" * 32 + b'"}')
        if request.full_url.endswith("/sendVideo"):
            return Answer(b'{"ok": true, "result": {"message_id": 7}}')
        return Answer(b'{"ok": true}')

    monkeypatch.setattr(send.urllib.request, "urlopen", urlopen)
    assert send.register(package, tmp_path, "https://api.test", "admin-secret") == "a" * 32
    assert send.send_for_approval(package, tmp_path, "123:bot-secret", "4242") == 7
    urls = [r.full_url for r in sent]
    assert urls[1].endswith("/v1/admin/promo/0123456789abcdef/video.mp4")
    assert sent[0].headers["Authorization"] == "Bearer admin-secret"
    assert {r.get_header("User-agent") for r in sent} == {"Wardly promo"}
    assert b"promo:all:0123456789abcdef" in sent[2].data
    assert json.loads(sent[3].data)["reply_to_message_id"] == 7
    assert "secret" not in capsys.readouterr().out


def test_the_coach_demo_cards_come_from_the_real_pipeline():
    from scripts.promo import coach_demo

    profile = {
        "key_escape_abilities": ["Blink"],
        "key_defensive_abilities": [],
        "key_fight_abilities": ["Mana Void"],
    }
    cards = coach_demo.cards("antimage", profile, "carry", lang="en")
    by_moment = {c["moment"]: c for c in cards}
    assert set(by_moment) == {"fall", "stun"}
    assert (
        "Blink" in by_moment["fall"]["action"] and by_moment["fall"]["decision_point"] == "LOW_HP"
    )
    assert by_moment["stun"]["decision_point"] == "DISABLED_STATUS"
    assert by_moment["stun"]["action"].startswith("The moment the disable ends")


def test_format_weights_move_only_with_enough_numbers():
    from scripts.promo import weights

    few = [{"format": "coach", "status": "scheduled", "views": 900}] * 2
    assert weights.multipliers(few) == {}
    posts = (
        [{"format": "coach", "status": "scheduled", "views": v} for v in (900, 1200, 1500)]
        + [{"format": "meta", "status": "published", "views": v} for v in (100, 200, 300)]
        + [{"format": "hero", "status": "rejected", "views": 5000}]
    )
    found = weights.multipliers(posts)
    assert found["coach"] > 1 > found["meta"]
    assert "hero" not in found  # a rejected video says nothing


def test_format_weights_read_names_itself_and_never_stops_the_video(monkeypatch, tmp_path, capsys):
    from scripts.promo import weights

    monkeypatch.setenv("API_URL", "https://api.test")
    monkeypatch.setenv("API_ADMIN_TOKEN", "admin-secret")
    monkeypatch.setattr(topics, "WEIGHTS_FILE", tmp_path / "weights.json")
    seen = []

    def refused(request, timeout):
        seen.append(request)
        raise weights.urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(weights.urllib.request, "urlopen", refused)
    weights.main()
    assert seen[0].get_header("User-agent") == "Wardly promo"
    assert not (tmp_path / "weights.json").exists()
    out = capsys.readouterr().out
    assert "weights unchanged: HTTPError" in out and "secret" not in out


def test_quality_findings_become_check_annotations_on_actions(monkeypatch, capsys):
    from scripts.promo import package

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    package.annotate("error", "у відео немає голосу")
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    package.annotate("error", "100% тиші\nдругий рядок")
    assert capsys.readouterr().out == "::error title=Promo quality::100%25 тиші%0Aдругий рядок\n"


def test_pictures_load_from_a_relative_output_folder(monkeypatch, tmp_path):
    # The workflow passes --out promo-out: the page still needs file:// URIs.
    from scripts.promo import render

    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo-out").mkdir()
    (tmp_path / "promo-out" / "render-axe.png").write_bytes(b"png")
    timeline = [{"data": {"hero": "axe"}}]
    assets = render.assets_for(timeline, Path("promo-out"), download=False)
    assert assets["render:axe"] == (tmp_path / "promo-out" / "render-axe.png").as_uri()
