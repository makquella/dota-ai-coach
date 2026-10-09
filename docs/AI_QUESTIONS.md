# AI coach questions: one run per request (0.53.52)

«Спросить тренера» stays a synchronous request, but its lifetime is bounded
and a lost response no longer costs a second provider call.

- **Request id.** The renderer sends `request_id` (`ask-<uuid>`, pattern
  `^[A-Za-z0-9_-]{8,64}$`) with each question; `app/ask_runs.py` runs the
  question once per id. The same id again — the launcher retrying after a lost
  answer — joins the run in progress or returns its stored result. An id is
  bound to its scope (`match:<account>:<match>:<lang>` or
  `career:<account>:<lang>`); reusing it elsewhere is `bad_request`.
- **Duplicate questions.** The same question (whitespace and case folded) in
  the same scope while one is running joins that run, so a double click without
  an id costs one call.
- **Status.** `GET /player/asks/{request_id}`: `unknown`, `running`
  (`elapsed_s`, `waiters`) or `done` with the exact result. The renderer reads it
  every 3 s (up to 30 times, while the card is on screen) when the launcher's
  wait timed out or the backend answered `pending`.
- **Deadline and attempts.** Two attempts at most (the fact-check retry), and
  the second one is not started after `ASK_DEADLINE_SECONDS` (75 s): the error is
  `timeout`. Each call keeps its 60 s provider timeout, so an answer or an error
  comes within about 135 s, under the launcher's 150 s wait. A joining request
  waits as long, then answers `pending`.
- **History.** The stored last five Q&A per match/career are read and written
  under one lock, so two questions answered at the same time both stay.
- **Memory only.** Runs live in memory; at most 32 finished ones are kept, the
  running ones always. A restart forgets them (the stored history stays).

Tests: `backend/tests/test_ask_runs.py` (same id once, a retry and a double
click join a running call, scope binding and validation, no second attempt
past the deadline, two concurrent questions both kept, bounds, a joiner's wait).
