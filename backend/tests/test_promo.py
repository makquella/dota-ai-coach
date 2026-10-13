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

from scripts.promo import media, quality, scenes, script, send, topics, voice  # noqa: E402


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


def test_percent_words_agree_with_the_number():
    said = [script.percent_said(n) for n in (1, 2, 5, 11, 21, 53, 112)]
    assert said == [
        "1 відсоток",
        "2 відсотки",
        "5 відсотків",
        "11 відсотків",
        "21 відсоток",
        "53 відсотки",
        "112 відсотків",
    ]


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
    assert line[1]["subs"][-1]["end"] <= line[1]["start"] + 3.5 + 0.3 + 1e-6
    assert all(len(s["text"]) <= scenes.SUB_CHARS + 12 for s in line[1]["subs"])
    page = scenes.page("meta", line, {}, 0)
    assert page.count('class="scene scene-') == 3 and "window.renderAt" in page
    assert "Мета тижня" in page  # the pill


def test_the_approval_message_fits_and_the_buttons_name_the_package(monkeypatch, tmp_path, capsys):
    package = _package(quality={"ok": True, "errors": [], "warnings": ["вимова: Glimpse"]})
    assert len(send.approval_caption(package)) <= 1024
    buttons = [b for row in send.keyboard(package["id"])["inline_keyboard"] for b in row]
    assert {b["callback_data"] for b in buttons} == {
        f"promo:{a}:{package['id']}" for a in ("all", "tg", "yt", "no")
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


def test_a_refused_request_names_the_reason_without_the_bot_token(monkeypatch):
    import io

    def refused(request, timeout):
        raise send.urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"description": "chat not found"}'),
        )

    monkeypatch.setattr(send.urllib.request, "urlopen", refused)
    with pytest.raises(SystemExit) as stopped:
        send._request("https://api.telegram.org/bot123:bot-secret/sendVideo", method="POST")
    message = str(stopped.value)
    assert "HTTP 400" in message and "chat not found" in message
    assert "/bot***/sendVideo" in message and "bot-secret" not in message


def test_words_get_their_times_from_the_voice_alignment():
    alignment = {
        "characters": list("Hi  Sven!"),
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7],
        "character_end_times_seconds": [0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    }
    assert voice.words_from_alignment(alignment) == [
        {"word": "Hi", "start": 0.0, "end": 0.2},
        {"word": "Sven!", "start": 0.3, "end": 0.8},
    ]


def test_elevenlabs_voice_writes_a_wav_and_never_leaks_the_key(monkeypatch, tmp_path):
    import base64
    import io
    import wave

    assert voice.synthesize("Привіт", tmp_path / "none.wav") is None  # no key: silent
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-secret")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    sent = []
    pcm = b"\x01\x00" * voice.RATE  # one second

    class Answer:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(
                {
                    "audio_base64": base64.b64encode(pcm).decode(),
                    "alignment": {
                        "characters": list("Так Sven"),
                        "character_start_times_seconds": [i * 0.1 for i in range(8)],
                        "character_end_times_seconds": [i * 0.1 + 0.1 for i in range(8)],
                    },
                }
            ).encode()

    def urlopen(request, timeout):
        sent.append(request)
        return Answer()

    monkeypatch.setattr(voice.urllib.request, "urlopen", urlopen)
    path, words = voice.synthesize("Так Sven", tmp_path / "v.wav", previous="До", following="Після")
    assert voice.duration(path) == pytest.approx(1.0)
    assert [w["word"] for w in words] == ["Так", "Sven"]
    body = json.loads(sent[0].data)
    assert (
        body["text"] == "Так Sven"
        and body["previous_text"] == "До"
        and body["next_text"] == "Після"
    )
    assert (
        voice.DEFAULT_VOICE in sent[0].full_url and sent[0].get_header("Xi-api-key") == "el-secret"
    )

    def refused(request, timeout):
        raise voice.urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"invalid key"}')
        )

    monkeypatch.setattr(voice.urllib.request, "urlopen", refused)
    with pytest.raises(SystemExit) as stopped:
        voice.synthesize("Так", tmp_path / "x.wav")
    assert "HTTP 401" in str(stopped.value) and "el-secret" not in str(stopped.value)
    with wave.open(str(path)) as audio:
        assert audio.getframerate() == voice.RATE


def test_the_crop_follows_the_motion():
    w, h = 96, 54
    still = bytes(w * h)
    moving = bytearray(still)
    for y in range(10, 20):
        for x in range(70, 80):
            moving[y * w + x] = 200
    left, middle = media.motion_focus(still + bytes(moving) + still, w, h)
    window = round(h * media.CLIP_ZOOM * 9 / 16) / w
    assert left <= 70 / w < left + window and left + window >= 80 / w - 1e-9
    assert middle == pytest.approx(14.5 / h, abs=0.02)
    assert media.motion_focus(still * 3, w, h)[1] == 0.5  # nothing moves: the middle


def _feed(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    (root / "herolist.json").write_text(
        json.dumps(
            {"result": {"data": {"heroes": [{"id": 27, "name": "npc_dota_hero_shadow_shaman"}]}}}
        )
    )
    (root / "hero-shadow_shaman.json").write_text(
        json.dumps(
            {
                "result": {
                    "data": {
                        "heroes": [
                            {
                                "abilities": [
                                    {"name": "shadow_shaman_voodoo", "name_loc": "Hex"},
                                    {"name": "shadow_shaman_shackles", "name_loc": "Shackles"},
                                    {"name": "generic_hidden", "name_loc": "Hidden"},
                                ]
                            }
                        ]
                    }
                }
            }
        )
    )
    (root / "itemlist.json").write_text(
        json.dumps(
            {
                "result": {
                    "data": {
                        "itemabilities": [
                            {
                                "name": "item_recipe_black_king_bar",
                                "name_english_loc": "Black King Bar Recipe",
                            },
                            {"name": "item_black_king_bar", "name_english_loc": "Black King Bar"},
                        ]
                    }
                }
            }
        )
    )
    return media.Library(tmp_path, online=False)


def test_a_card_finds_its_ability_or_item_in_valves_data(tmp_path):
    library = _feed(tmp_path)
    assert [a["key"] for a in library.abilities("shadow_shaman")] == [
        "shadow_shaman_voodoo",
        "shadow_shaman_shackles",
    ]
    assert (
        library.ability_in("shadow_shaman", "Використайте Shackles зараз")["key"]
        == "shadow_shaman_shackles"
    )
    assert library.ability_in("shadow_shaman", "Hexagon") is None  # whole names only
    assert library.item_in("Одразу натисніть Black King Bar.")["key"] == "black_king_bar"
    assert media.threat("stun", "sven", 0)[0] != "sven"


def test_scenes_play_the_frames_valve_gives_and_stay_whole_without_them(tmp_path):
    library = _feed(tmp_path)
    raw = [
        {"kind": "hook", "voice": "Граєш на Shadow Shaman?", "data": {"hero": "shadow_shaman"}},
        {
            "kind": "card",
            "voice": "Тебе застанили. Використайте Shackles.",
            "data": {
                "hero": "shadow_shaman",
                "mode": "urgent",
                "action": "Використайте Shackles",
                "reason": "x",
                "moment": "stun",
            },
        },
    ]
    words = [
        None,
        [
            {"word": "Тебе", "start": 0.0, "end": 0.3},
            {"word": "застанили.", "start": 0.3, "end": 0.9},
        ],
    ]
    line = scenes.timeline(raw, [1.5, 3.0], words)
    assert line[1]["subs"][0]["words"][0]["s"] == pytest.approx(line[1]["start"])
    assert [w["word"] for w in line[0]["words"]][:2] == ["Граєш", "на"]  # estimated for the hook
    # offline and nothing downloaded: no sequences, still a whole page
    assert media.prepare(line, library, 0) == {}
    page = scenes.page("coach", line, {}, 0)
    assert "ОГЛУШЕНИЙ" in page and 'data-impact="1.00"' in page and "data-seq" not in page
    # with frames: the hero moves, the enemy's stun and the named ability play
    line[0]["media"] = {"idle": "idle:shadow_shaman", "bg": "clip:shadow_shaman_shackles"}
    line[1]["media"] = {
        "idle": "idle:shadow_shaman",
        "threat": "clip:sven_storm_bolt",
        "pay": "clip:shadow_shaman_shackles",
        "pay_name": "Shackles",
    }
    seqs = {
        name: {"frames": ["file:///f1.webp", "file:///f2.webp"], "fps": 24}
        for name in ("idle:shadow_shaman", "clip:sven_storm_bolt", "clip:shadow_shaman_shackles")
    }
    page = scenes.page("coach", line, {"seqs": seqs}, 0)
    assert 'data-seq="clip:sven_storm_bolt"' in page and 'data-seq="idle:shadow_shaman"' in page
    assert "data-pay=" in page and "Shackles" in page and "window.__SEQS__" in page


def test_the_draft_video_takes_its_enemy_item_and_card_from_the_app():
    from scripts.promo import draft_demo

    found = draft_demo.card("Phantom Lancer")
    assert found["key"] == "phantom_lancer" and found["item"]["name"] == "Maelstrom"
    assert found["title"] == "Проти їхнього драфту: Maelstrom"  # the overlay's own text
    assert "Phantom Lancer" in found["reason"]
    assert all(draft_demo.card(e) for e in draft_demo.enemies())  # every enemy has an answer
    item = script.draft(found, random.Random(1), "0.56.2")
    assert item.format == "draft" and item.topic == "phantom_lancer"
    assert [s.kind for s in item.scenes] == ["hook", "card", "cta"]
    card = item.scenes[1]
    assert card.data["enemy"] == "phantom_lancer" and card.data["moment"] == "draft"
    assert "Phantom Lancer" in card.voice and "Wardly" in card.voice and "Maelstrom" in card.voice
    assert "#maelstrom" in item.caption and "promo-draft" in item.caption
    assert quality.check(
        {**_package(), "caption": item.caption, "script": item.to_dict(), "sources": item.sources},
        {"seconds": 30, "width": 1080, "height": 1920, "audio": True, "bytes": 1},
    )["ok"]


def test_draft_videos_rotate_their_enemies():
    pool = ["Phantom Lancer", "Spectre", "Meepo"]
    keys = {"Phantom Lancer": "phantom_lancer", "Spectre": "spectre", "Meepo": "meepo"}
    history = [
        {"format": "draft", "topic": "phantom_lancer"},
        {"format": "draft", "topic": "spectre"},
    ]
    assert topics.next_enemy(pool, keys, history, random.Random(0)) == "Meepo"
    assert topics.next_enemy(pool, keys, history * 5, random.Random(0)) == "Meepo"


def test_the_card_hits_as_the_voice_says_wardly():
    raw = [
        {
            "kind": "card",
            "voice": "Проти Spectre тобі знадобиться інший підхід. Wardly підкаже.",
            "data": {"action": "x", "moment": "draft", "enemy": "spectre", "enemy_name": "Spectre"},
        }
    ]
    words = [
        [
            {"word": w, "start": i * 0.4, "end": i * 0.4 + 0.3}
            for i, w in enumerate(raw[0]["voice"].split())
        ]
    ]
    line = scenes.timeline(raw, [3.0], words)
    assert scenes.card_moment(line[0]) == pytest.approx(6 * 0.4)
    page = scenes.page("draft", line, {}, 0)
    assert 'data-impact="2.40"' in page and "ПРОТИ SPECTRE" in page and "Проти драфту" in page
