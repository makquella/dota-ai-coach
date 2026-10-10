# Оцінка порад після матчу (0.53.56)

Аудит (розділ D): `advice_follow.py` бачить лише смерть після термінової поради — це непрямий сигнал. Щоб відрізнити недоречну чи повторювану пораду від правильної, але проігнорованої, гравець після матчу може позначити кілька карток «Підказки під час матчу»: «Корисно», «Не до речі», «Повторювалося». Під час гри оверлей нічого не питає.

- Ключ картки — `<t>:<dp>` (секунда матчу й decision point), `advice_feedback.advice_key`. Бекенд додає до кожної картки розбору `key` і поточну позначку `feedback`, до деталей — `advice_feedback`.
- `POST /player/matches/{id}/advice-feedback {key, verdict}`; `verdict: null` знімає позначку. Хибний ключ чи вердикт — 400, невідомий матч — 404.
- Зберігається в meta `advice_feedback:<account>:<match>` (JSON-об'єкт, не більше 200 позначок на матч), потрапляє в резервну копію історії й повертається під час відновлення (перевірка форми через `META_JSON`). Нікуди не надсилається.
- `GET /player/advice-feedback` і `/diagnostics` `player.advice_feedback`: лічильники за decision point, без тексту порад. Хмарна агрегація — лише в майбутньому, окремим opt-in з allowlist і правкою політики конфіденційності.

## Тихіші поради (0.55.0)

- `advice_feedback.quieter_decisions`: decision point із 3+ відмітками, з яких 60%+ — «Не до речі» або «Повторювалося», стає «тихішим». Ніколи: `LOW_HP`, `DISABLED_STATUS`, `NO_ADVICE`, `SOFT_STATUS`, розбори смертей і `UNSCALED_DECISIONS` (безпека).
- Зведення (`GET /player/advice-feedback`, `career.advice_feedback`) містить `quieter`. `player_api.refresh_quieter_advice` передає його в `ADVICE_SCHEDULER.set_quieter` під час запуску, після кожної відмітки й після зміни акаунта; список переживає `reset()` (новий матч).
- У планувальнику (`_game_time_spacing_remaining_locked`) для тихішої coaching-поради мінімальна пауза множиться на `QUIETER_GAP_FACTOR` (2). Термінові поради не змінюються.
- «Прогрес»: картка «Ваші відмітки на порадах» (`adviceMarksCard`, підписи видів порад — `adviceKinds` у `match-texts.js`), лише для всіх героїв.

Тести: `backend/tests/test_advice_feedback.py`, `test_advice_frequency.py` (тихіші поради на реплеї) (справжній матч із GSI, зміна й зняття позначки, помилки, зведення без тексту, перенесення через резервну копію, пошкоджені дані).
