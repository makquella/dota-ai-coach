"""AI questions: one provider run per request id, joining a run in progress,
the total deadline and the shared Q&A history (ask_runs.py, player_service)."""

from __future__ import annotations

import threading
from typing import Any

from test_coach_ai import MATCH_ID, FakeLLM, _reviewed_match

from app import player_service
from app.ask_runs import KEEP_FINISHED, AskRuns
from app.player_api import PLAYER_SERVICE

GOOD = {"answer": "Главное — смерти: их было 9, и каждая отодвигала ваш тайминг."}
OTHER = {"answer": "Смертей было 9: начните с них."}
ASK = f"/player/matches/{MATCH_ID}/ask?lang=ru"


class BlockingLLM(FakeLLM):
    """Holds every call until released, so a second request meets the first running."""

    def __init__(self, *answers: Any) -> None:
        super().__init__(*answers)
        self.entered = threading.Event()
        self.release = threading.Event()

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.entered.set()
        assert self.release.wait(10)
        return super().complete(messages, **kwargs)


def _post(client, question: str, request_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"question": question}
    if request_id:
        body["request_id"] = request_id
    return client.post(ASK, json=body).json()


def test_the_same_request_id_never_calls_the_provider_twice(client, tmp_path):
    llm = FakeLLM(GOOD)
    _reviewed_match(client, tmp_path, llm)
    first = _post(client, "Почему я проиграл?", "req-0001-aaaa")
    again = _post(client, "Почему я проиграл?", "req-0001-aaaa")
    assert first["ok"] is True and again == first
    assert len(llm.calls) == 1
    status = client.get("/player/asks/req-0001-aaaa").json()
    assert status == {"state": "done", "result": first}
    assert client.get("/player/asks/req-unknown-1").json() == {"state": "unknown"}
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    assert [q["question"] for q in detail["questions"]] == ["Почему я проиграл?"]


def test_a_retry_while_running_joins_the_run(client, tmp_path):
    llm = BlockingLLM(GOOD)
    _reviewed_match(client, tmp_path, llm)
    results: list[dict[str, Any]] = []
    threads = [
        threading.Thread(target=lambda: results.append(_post(client, "Почему?", "req-0002-bbbb"))),
        # A double click without an id: same match, same question.
        threading.Thread(target=lambda: results.append(_post(client, "  почему? "))),
    ]
    threads[0].start()
    assert llm.entered.wait(5)
    status = client.get("/player/asks/req-0002-bbbb").json()
    assert status["state"] == "running" and status["elapsed_s"] >= 0
    threads[1].start()
    while client.get("/player/asks/req-0002-bbbb").json().get("waiters") != 1:
        threads[1].join(0.01)
    llm.release.set()
    for thread in threads:
        thread.join(10)
    assert len(results) == 2 and results[0] == results[1] and results[0]["ok"] is True
    assert len(llm.calls) == 1


def test_a_request_id_belongs_to_one_question_scope(client, tmp_path):
    llm = FakeLLM(GOOD)
    _reviewed_match(client, tmp_path, llm)
    assert _post(client, "Почему?", "req-0003-cccc")["ok"] is True
    other = client.post(
        "/player/career/ask?lang=ru", json={"question": "Почему?", "request_id": "req-0003-cccc"}
    ).json()
    assert other == {"ok": False, "code": "bad_request"}
    bad = client.post(ASK, json={"question": "Почему?", "request_id": "short"})
    assert bad.status_code == 422
    assert client.get("/player/asks/bad id!").status_code in {404, 422}


def test_no_second_attempt_after_the_deadline(client, tmp_path, monkeypatch):
    invented = {"answer": "Invoker убил вас на 17:43, когда у вас было 4321 золота."}
    llm = FakeLLM(invented, GOOD)
    _reviewed_match(client, tmp_path, llm)
    monkeypatch.setattr(player_service, "ASK_DEADLINE_SECONDS", 0.0)
    assert _post(client, "Кто меня убил?") == {"ok": False, "code": "timeout"}
    assert len(llm.calls) == 1
    monkeypatch.setattr(player_service, "ASK_DEADLINE_SECONDS", 75.0)
    # With time left, an unverified first answer gets its second attempt.
    llm.answers = [invented, GOOD]
    assert _post(client, "Кто меня убил?")["ok"] is True
    assert len(llm.calls) == 3


def test_concurrent_questions_both_stay_in_the_history(client, tmp_path):
    llm = FakeLLM(GOOD, OTHER)
    _reviewed_match(client, tmp_path, llm)
    start = threading.Barrier(2)

    def ask(question: str, request_id: str) -> None:
        start.wait(5)
        assert _post(client, question, request_id)["ok"] is True

    threads = [
        threading.Thread(target=ask, args=("Почему я проиграл?", "req-0004-dddd")),
        threading.Thread(target=ask, args=("Что купить раньше?", "req-0005-eeee")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)
    detail = client.get(f"/player/matches/{MATCH_ID}?lang=ru").json()
    assert sorted(q["question"] for q in detail["questions"]) == [
        "Почему я проиграл?",
        "Что купить раньше?",
    ]
    assert PLAYER_SERVICE.asks.running() == 0


def test_finished_runs_are_bounded_and_running_ones_kept():
    runs = AskRuns()
    gate = threading.Event()
    worker = threading.Thread(
        target=lambda: runs.run(
            "s", "q", "keep-running", lambda: gate.wait(5) and {"ok": True}, wait_s=1
        )
    )
    worker.start()
    for index in range(KEEP_FINISHED + 10):
        runs.run("s", f"q{index}", f"done-{index:04d}", lambda: {"ok": True}, wait_s=1)
    assert runs.status("done-0000") == {"state": "unknown"}
    assert runs.status(f"done-{KEEP_FINISHED + 9:04d}")["state"] == "done"
    assert runs.status("keep-running")["state"] == "running"
    gate.set()
    worker.join(5)
    assert runs.status("keep-running") == {"state": "done", "result": {"ok": True}}


def test_a_joiner_gives_up_after_its_wait():
    runs = AskRuns()
    gate = threading.Event()
    worker = threading.Thread(
        target=lambda: runs.run(
            "s", "q", "slow-0001", lambda: gate.wait(5) and {"ok": True}, wait_s=1
        )
    )
    worker.start()
    while runs.running() == 0:
        pass
    assert runs.run("s", "q", "slow-0001", lambda: {"ok": "never"}, wait_s=0.05) == {
        "ok": False,
        "code": "pending",
        "request_id": "slow-0001",
    }
    gate.set()
    worker.join(5)
