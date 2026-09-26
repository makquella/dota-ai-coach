"""AI coach: settings, generation on the AI job thread, fact check, cache."""

from __future__ import annotations

import json
from typing import Any

import pytest
from match_fixtures import (
    MATCH_ID,
    ME,
    FakeOpenDota,
    gsi_match_stream,
    opendota_match,
    recent_matches,
)

from app.coach_llm import CoachLLM, CoachLLMError, settings_from
from app.coach_review import FactChecker
from app.player_api import PLAYER_SERVICE

GOOD_MATCH_REVIEW = {
    "summary": (
        "Матч решила линия: к 10:00 у вас 36 добиваний против 65 у Anti-Mage. "
        "Из-за этого Maelstrom пришёл только к 26:00."
    ),
    "turning_points": [{"time": "4:00", "text": "Первая смерть от Shadow Fiend на линии."}],
    "mistakes": [
        {
            "title": "Проигранная линия",
            "detail": "36 добиваний к 10:00 против 65 у Anti-Mage.",
            "fix": "Добивайте под своей вышкой, пока Shadow Fiend давит.",
        }
    ],
    "strengths": [],
    "next_game": ["Maelstrom к 20:00.", "Не больше 2 смертей на линии."],
}

GOOD_CAREER_REVIEW = {
    "summary": "Juggernaut — ваш основной герой. Главная проблема — серии смертей.",
    "patterns": [
        {
            "title": "Серии смертей",
            "detail": "Смерти идут подряд после первой ошибки.",
            "fix": "После смерти сначала посмотрите на карту.",
        }
    ],
    "strengths": ["Хорошая линия."],
    "plan": ["Не больше 5 смертей за матч.", "Первый предмет к 15:00."],
}


class FakeLLM:
    """Scripted answers; records every request."""

    label = {"provider": "groq", "model": "openai/gpt-oss-120b"}

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.calls.append(messages)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)

    def check(self) -> None:
        pass


def _service(tmp_path, llm, *, client=None):
    PLAYER_SERVICE.configure(tmp_path / "svc", client=client, auto_start=False, llm=llm)
    return PLAYER_SERVICE


def _reviewed_match(client, tmp_path, llm):
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match(good=False)})
    service = _service(tmp_path, llm, client=fake)
    client.post("/player/link", json={"steam": str(ME)})
    service.fetch_match(MATCH_ID, request_parse=False)
    service.jobs.run_pending(until=float("inf"))
    return service


def test_ai_is_off_without_a_key(client, tmp_path):
    _reviewed_match(client, tmp_path, None)
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    assert detail["coach"] == {"state": "off"}
    assert client.get("/player").json()["ai"] == {"configured": False}
    assert client.get("/player/career?lang=ru").json()["coach"]["state"] in ("off", "not_enough")


def test_match_review_is_generated_in_the_background_and_cached(client, tmp_path):
    llm = FakeLLM(GOOD_MATCH_REVIEW)
    service = _reviewed_match(client, tmp_path, llm)
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "pending" and not llm.calls

    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "ready" and coach["stale"] is False
    assert coach["review"]["mistakes"][0]["title"] == "Проигранная линия"
    assert coach["review"]["turning_points"] == [
        {"time": "4:00", "text": "Первая смерть от Shadow Fiend на линии."}
    ]
    assert coach["provider_label"] == "Groq" and coach["model"] == "openai/gpt-oss-120b"
    # Cached: polling does not call the model again.
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    assert len(llm.calls) == 1

    # The prompt: Russian answer, the rule findings, no account id or player names.
    system, user = llm.calls[0][0]["content"], llm.calls[0][1]["content"]
    assert "Write in Russian" in system
    facts = json.loads(user)
    assert facts["hero"] == "Juggernaut" and facts["same_role_opponent"]["hero"] == "Anti-Mage"
    assert any(f["title"] == "Поздний Maelstrom" for f in facts["findings_to_improve"])
    assert str(ME) not in user and "Player 1" not in user

    # Another language is another review.
    client.get(f"/player/matches/{MATCH_ID}?lang=en")
    service.ai_jobs.run_pending(until=float("inf"))
    assert "Write in English" in llm.calls[1][0]["content"]


def test_invented_facts_are_dropped_sentence_by_sentence(client, tmp_path):
    answer = json.loads(json.dumps(GOOD_MATCH_REVIEW))
    answer["summary"] += " Pudge дважды поймал вас с хука."
    answer["next_game"].append("Фармите 777 золота в минуту.")
    llm = FakeLLM(answer)
    service = _reviewed_match(client, tmp_path, llm)
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    review = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]["review"]
    assert "Pudge" not in review["summary"] and "Anti-Mage" in review["summary"]
    assert review["next_game"] == GOOD_MATCH_REVIEW["next_game"]
    assert len(llm.calls) == 1


def test_mostly_invented_answer_gets_one_retry(client, tmp_path):
    invented = {
        **GOOD_MATCH_REVIEW,
        "summary": "Вы проиграли из-за 14 смертей от Pudge.",
        "mistakes": [
            {"title": "Смерти", "detail": "14 смертей к 18:30.", "fix": "Купите 3 варда."}
        ],
    }
    llm = FakeLLM(invented, GOOD_MATCH_REVIEW)
    service = _reviewed_match(client, tmp_path, llm)
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "ready" and len(llm.calls) == 2
    retry = llm.calls[1][-1]["content"]
    assert "Pudge" in retry and "14" in retry and "18:30" not in coach["review"]["summary"]


def test_unverifiable_answer_is_an_error_until_asked_again(client, tmp_path):
    invented = {**GOOD_MATCH_REVIEW, "summary": "Вы проиграли из-за 14 смертей от Pudge."}
    invented["mistakes"] = [{"title": "Смерти", "detail": "14 смертей.", "fix": "Не умирайте."}]
    llm = FakeLLM(invented)
    service = _reviewed_match(client, tmp_path, llm)
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach == {"state": "error", "error": "unverified"}
    service.ai_jobs.run_pending(until=float("inf"))
    assert len(llm.calls) == 2  # no automatic retries after the error

    llm.answers = [GOOD_MATCH_REVIEW]
    assert client.post(f"/player/matches/{MATCH_ID}/coach?lang=ru").json()["state"] == "pending"
    service.ai_jobs.run_pending(until=float("inf"))
    assert client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]["state"] == "ready"


def test_provider_errors_are_reported(client, tmp_path):
    llm = FakeLLM(CoachLLMError("rate_limited"))
    service = _reviewed_match(client, tmp_path, llm)
    client.get(f"/player/matches/{MATCH_ID}?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach == {"state": "error", "error": "rate_limited"}


GSI_MATCH_REVIEW = {
    "summary": "Juggernaut хорошо начал линию, но потом умирал сериями.",
    "mistakes": [
        {
            "title": "Серия смертей",
            "detail": "Смерти шли одна за другой в середине игры.",
            "fix": "После смерти сначала посмотрите на карту.",
        }
    ],
    "next_game": ["Не больше 2 смертей подряд."],
}


def test_live_match_waits_for_the_replay_and_refreshes_when_facts_change(client, tmp_path):
    llm = FakeLLM(GSI_MATCH_REVIEW)
    fake = FakeOpenDota(matches={MATCH_ID: opendota_match(good=False)})
    service = _service(tmp_path, llm, client=fake)
    for payload in gsi_match_stream(win=False):
        client.post("/gsi", json=payload)
    # OpenDota has not parsed the replay yet: the coach waits for the full data.
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "waiting" and not llm.calls
    # ...unless the player asks now.
    client.post(f"/player/matches/{MATCH_ID}/coach?lang=ru")
    service.ai_jobs.run_pending(until=float("inf"))
    assert client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]["state"] == "ready"

    # The parsed replay arrives: the old review stays visible while a new one is made.
    service.jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "pending" and coach["stale"] is True and coach["review"]
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()["coach"]
    assert coach["state"] == "ready" and coach["stale"] is False
    assert len(llm.calls) == 2


def test_career_review(client, tmp_path):
    recent = recent_matches(12)
    fake = FakeOpenDota(
        matches={
            row["match_id"]: opendota_match(good=row["radiant_win"], match_id=row["match_id"])
            for row in recent
        },
        recent=recent,
    )
    llm = FakeLLM(GOOD_CAREER_REVIEW)
    service = _service(tmp_path, llm, client=fake)
    client.post("/player/link", json={"steam": str(ME)})
    service.jobs.run_pending(until=float("inf"))
    assert client.get("/player/career?lang=ru").json()["coach"]["state"] == "pending"
    service.ai_jobs.run_pending(until=float("inf"))
    coach = client.get("/player/career?lang=ru").json()["coach"]
    assert coach["state"] == "ready" and coach["review"]["plan"][0].startswith("Не больше 5")
    facts = json.loads(llm.calls[0][1]["content"])
    assert len(facts["recent_matches"]) == 10 and facts["rank"] == "Легенда 4"
    assert facts["recurring_problems"]


def test_career_needs_a_few_reviewed_matches(client, tmp_path):
    _reviewed_match(client, tmp_path, FakeLLM(GOOD_CAREER_REVIEW))
    coach = client.get("/player/career?lang=ru").json()["coach"]
    assert coach == {"state": "not_enough", "need": 3}


def test_ai_settings_api_never_returns_the_key(client, tmp_path):
    _service(tmp_path, None)
    assert client.get("/player/ai").json()["configured"] is False
    bad = client.post("/player/ai", json={"provider": "openai", "api_key": "x"})
    assert bad.status_code == 400
    saved = client.post("/player/ai", json={"provider": "groq", "api_key": "gsk_secret_abcd"})
    body = saved.json()
    assert body["configured"] and body["provider"] == "groq" and body["key_hint"] == "…abcd"
    assert body["model"] == "openai/gpt-oss-120b" and body["source"] == "app"
    assert "gsk_secret_abcd" not in json.dumps(body)
    assert "gsk_secret_abcd" not in json.dumps(client.get("/player").json())
    assert client.get("/player").json()["ai"] == {"configured": True}
    assert client.delete("/player/ai").json()["configured"] is False


def test_env_key_is_used_when_the_player_has_none(tmp_path):
    env = settings_from({"provider": "openrouter", "api_key": "sk-or-env-1234"}, source="env")
    PLAYER_SERVICE.configure(tmp_path / "svc", client=None, auto_start=False, env_ai=env)
    status = PLAYER_SERVICE.ai_status()
    assert status["source"] == "env" and status["model"] == "openai/gpt-oss-120b:free"
    PLAYER_SERVICE.set_ai("groq", "gsk_app_key_9999")
    assert PLAYER_SERVICE.ai_status()["source"] == "app"


class _Response:
    def __init__(self, status: int, body: Any) -> None:
        self.status_code = status
        self._body = body

    def json(self) -> Any:
        return self._body


class _Session:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _Response:
        self.requests.append({"url": url, **kwargs})
        return self.response


def _client(provider: str, response: _Response) -> tuple[CoachLLM, _Session]:
    settings = settings_from({"provider": provider, "api_key": "key-12345678"}, source="app")
    assert settings is not None
    session = _Session(response)
    return CoachLLM(settings, session=session), session


def test_llm_client_request_and_errors():
    llm, session = _client("groq", _Response(200, {"choices": [{"message": {"content": "{}"}}]}))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "{}"
    request = session.requests[0]
    assert request["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer key-12345678"
    assert request["json"]["model"] == "openai/gpt-oss-120b"
    assert request["json"]["reasoning_effort"] == "medium"
    assert request["json"]["response_format"] == {"type": "json_object"}

    llm, session = _client(
        "openrouter", _Response(200, {"choices": [{"message": {"content": "x"}}]})
    )
    llm.complete([{"role": "user", "content": "hi"}])
    assert session.requests[0]["json"]["reasoning"]["effort"] == "medium"

    for status, code in ((401, "invalid_key"), (429, "rate_limited"), (500, "bad_response")):
        llm, _ = _client("groq", _Response(status, {}))
        with pytest.raises(CoachLLMError) as error:
            llm.complete([{"role": "user", "content": "hi"}])
        assert error.value.code == code


def test_llm_client_retries_without_optional_parameters_on_http_400():
    class Session:
        def __init__(self) -> None:
            self.payloads: list[dict[str, Any]] = []

        def post(self, url: str, **kwargs: Any) -> _Response:
            self.payloads.append(json.loads(json.dumps(kwargs["json"])))
            if "response_format" in kwargs["json"]:
                return _Response(400, {})
            return _Response(200, {"choices": [{"message": {"content": "{}"}}]})

    settings = settings_from({"provider": "groq", "api_key": "key-12345678"}, source="app")
    assert settings is not None
    session = Session()
    assert CoachLLM(settings, session=session).complete([{"role": "user", "content": "x"}]) == "{}"
    assert len(session.payloads) == 2
    assert "response_format" not in session.payloads[1]
    assert "reasoning_effort" not in session.payloads[1]


def test_fact_checker_understands_number_formats():
    facts = json.dumps({"net_worth": 11500, "gpm_pct": 0.12, "kda": 2.4, "time": "26:00"})
    checker = FactChecker(facts, ["Black King Bar", "Maelstrom"])
    assert checker.problems("Ценность 11 500, лучше 12% игроков, KDA 2,4 к 26:00.") == []
    assert checker.problems("11.5k net worth, 3 deaths by minute 15.") == []
    assert checker.problems("Купите Black King Bar к 18:00.") == ["18:00", "Black King Bar"]
    # 14 000 net worth does not make "14 deaths" a fact.
    assert FactChecker(json.dumps({"nw": 14000}), []).problems("14 смертей, 14k золота") == ["14"]
