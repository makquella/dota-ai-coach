# План развития после аудита

Актуальная база: **0.53.0**, 64 героя с полным советником. Аудит от 7 октября 2026 исследовал `dd5a83c` (0.52.0); PR [#97](https://github.com/makquella/dota-ai-coach/pull/97) и [#99](https://github.com/makquella/dota-ai-coach/pull/99) уже слиты. Изменения аудита выходят как **0.53.1, 0.53.2 и далее**; новая minor-версия не нужна для каждого исправления.

Это текущий backlog. Старый продуктовый план сохранён в [архиве](archive/roadmap-before-2026-10-07.md), подробности облачного хранения — в [DATA_PLAN.md](DATA_PLAN.md). Подтверждённых P0 в аудите нет; security hardening и подтверждённые сбои данных остаются обязательными независимо от оценки трудозатрат.

| ID | Приоритет | Работа и приёмка | Состояние |
|---|---|---|---|
| F05 | P1 | Ошибка записи recommendation log сохраняет HTTP-ответ и попадает в diagnostics; запись восстанавливается после устранения ошибки | [PR #100](https://github.com/makquella/dota-ai-coach/pull/100), версия 0.53.1 |
| F09 | P1 | Короткий AGENTS, тонкий CLAUDE adapter, явные targeted checks вместо глобальных hooks; справочные сведения сохранены | Подготовлено в этом изменении |
| F08 | P1 | Проверить актуальные advisory ranges; обновить совместимые Electron/updater/build/Wrangler зависимости; clean install, unit suites, Windows build/smoke | Следующий этап; применимость advisory проверять отдельно |
| F07 | P1 | Зафиксировать Python runtime/dev/build зависимости и tools; единый путь установки в CI и packaging, воспроизводимый type baseline | Следующий этап |
| F01 | P1 | Durable pending finish → idempotent DB save → ack; restart и write-failure тесты сохраняют timeline | Не реализовано |
| F02 | P1 | Дедупликация running jobs, stop/join с deadline, безопасный lifetime store; настоящие threads + Events | Не реализовано |
| F03 | P1 | Валидация backup до записи и одна transaction с account linking; rollback на сбое, восстановление повреждённого cache | Не реализовано |
| F06 | P1 | Отдельные control/GSI tokens, Origin/Host checks и bounded body; реальный Dota config и launcher smoke совместимы | Не реализовано |
| F04 | P1 | Связать AI числа с метрикой и источником; начать с трёх findings, запретить metric swaps | Не реализовано; разбивать на slices |
| F10 | P2 | Согласованный runtime snapshot и ownership MatchMemory; concurrent publish/read/reset без disk/network под lock | Не реализовано |
| F11 | P2 | Atomic conditional transfer claims и conflict-safe insert; migrations + concurrency на local D1 | Не реализовано |
| F12 | P2 | DTO/contract tests важных player/detail/facts ответов и их JS consumers | Не реализовано |
| F13 | P2 | Извлекать jobs/locales/detail controller по одной границе с behavior/UI tests | Не реализовано |
| F14 | P2 | Locked mypy + baseline и blocking checks чистых модулей; долг не растёт | Не реализовано; текущий mypy остаётся nonblocking |
| F15 | P2 | Reusable validation проверяет тот же SHA до release publish | Не реализовано |
| F16 | P2 | Canonical npm syntax check, отмена superseded PR CI; затем meaningful-path Windows gating со стабильным required summary | Первая часть подготовлена в этом изменении; gating ещё нет |
| F17 | P2 | Trusted IPC sender/frame, navigation/popup guards, incremental CSP; реальные UI smoke checks | Не реализовано |

Ближайшие PR: dependency triage и Python locks; затем finish/queue/backup/auth как отдельные исправления с fault tests. Не ждать большого рефакторинга для подтверждённых потерь данных. Для поведения live-политики использовать sanitized role recordings и fixed-clock replay, для новых UI границ — настоящие DOM-сценарии.

Следующие продуктовые улучшения после safeguards: источники/покрытие данных в разборе, preview восстановления истории, rotating local backups, сопоставимость Progress между версиями правил. Метрики и сроки проверять на фактических данных; их наличие в плане не означает, что функции уже реализованы.

Developer runner `scripts/dev.py`, portable scoped hook adapter, local D1 harness и UI regression harness пока **не созданы**. До их внедрения использовать проверенные команды из [TESTING.md](TESTING.md) и [REFERENCE_COMMANDS.md](REFERENCE_COMMANDS.md). Новые helpers должны выбирать cwd и argv явно, учитывать staged/unstaged/untracked paths и не выполнять deploy, publish или платные AI вызовы.
