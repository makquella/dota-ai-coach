"""The overlay card while the player waits to respawn (app/death_screen.py)."""

from __future__ import annotations

from match_fixtures import gsi_match_stream

from app.death_screen import build_death_screen

BKB = {"name": "item_black_king_bar", "can_cast": True, "cooldown": 0}


def _screen(**overrides):
    args = {
        "death": {"t": 1080, "usable": ["item_black_king_bar"], "burst_s": 2},
        "place": {"zone": "mid", "side": "river", "count": 3, "minutes": 6},
        "respawn": 23,
        "gold": 1800,
        "buyback_cost": None,
        "minute": 18,
        "next_item": {"name": "Manta Style", "gold_left": 1500},
        "lang": "ru",
    }
    return build_death_screen(**{**args, **overrides})


def test_the_card_says_how_it_happened_and_what_to_do():
    card = _screen()
    assert card["title"] == "Возрождение через 23 с"
    assert card["lines"] == [
        "Убили за 2 с с высокого HP: поймали, когда вы были одни или на виду.",
        "Black King Bar был готов и не нажат — в следующий раз жмите при первом ударе.",
        "3-я смерть на центральной линии у реки за 6 мин — после возрождения идите в другое место.",
        "Купите Manta Style сейчас: золота хватает, курьер принесёт.",
    ]
    english = _screen(lang="en")
    assert english["lines"][2] == (
        "Death number 3 in the mid lane by the river in 6 min: after respawn, go somewhere else."
    )


def test_the_buy_line_keeps_the_buyback_gold_late():
    card = _screen(death={}, place=None, minute=35, buyback_cost=1500, gold=2400)
    assert card["lines"] == [
        "Купите части Manta Style: не хватает 600 золота. Оставьте 1500 на байбэк."
    ]
    # No buyback cost known after minute 30: no buy line (and nothing else: no card).
    assert _screen(death={}, place=None, minute=35, buyback_cost=None) is None
    # Without a known next item: spend on the next item in general.
    card = _screen(death={}, place=None, next_item=None, gold=900)
    assert card["lines"] == ["Потратьте 900 золота на следующий предмет — у фонтана это быстрее."]


def test_the_live_card_while_dead(client):
    stream = gsi_match_stream(death_minutes=(18,), step_seconds=1, minutes=19)[:-1]
    for payload in stream:
        before = 18 * 60 - payload["map"]["clock_time"]
        if 0 < before <= 6:
            payload["hero"]["health_percent"] = 12 * before
            payload["items"]["slot5"] = dict(BKB)
        if payload["map"]["clock_time"] > 18 * 60 + 5:
            break
        client.post("/gsi", json=payload)
    body = client.get("/overlay/recommendation?lang=ru").json()
    card = body["death_screen"]
    assert card["title"] == "Возрождение через 20 с"
    assert "Black King Bar был готов и не нажат" in card["lines"][0]


def _dead_client(client):
    stream = gsi_match_stream(death_minutes=(18,), step_seconds=1, minutes=19)[:-1]
    last = None
    for payload in stream:
        if 0 < 18 * 60 - payload["map"]["clock_time"] <= 6:
            payload["items"]["slot5"] = dict(BKB)
        if payload["map"]["clock_time"] > 18 * 60 + 5:
            break
        client.post("/gsi", json=payload)
        last = payload
    return last


def test_the_card_id_stays_while_the_gold_changes(client):
    last = _dead_client(client)
    first = client.get("/overlay/recommendation?lang=ru").json()["death_screen"]
    last["hero"]["gold"] = last["player"]["gold"] = (last["player"].get("gold") or 0) + 250
    last["player"]["gold_unreliable"] = (last["player"].get("gold_unreliable") or 0) + 250
    last["map"]["clock_time"] += 1
    client.post("/gsi", json=last)
    second = client.get("/overlay/recommendation?lang=ru").json()["death_screen"]
    assert first["id"] and second["id"] == first["id"]


def test_no_death_card_when_gsi_is_stale(client, monkeypatch):
    from app import main

    _dead_client(client)
    assert client.get("/overlay/recommendation?lang=ru").json().get("death_screen")
    monkeypatch.setattr(main, "_seconds_since_timestamp", lambda _timestamp: 60.0)
    body = client.get("/overlay/recommendation?lang=ru").json()
    assert body["status"] == "stale_gsi"
    assert "death_screen" not in body
