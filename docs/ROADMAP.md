# План развития после аудита

Актуальная база в main: **0.53.3**, 64 героя с полным советником. Аудит от 7 октября 2026 исследовал `dd5a83c` (0.52.0); PR #97, #99 и #100–#103 уже слиты. Изменения аудита выходят как **0.53.1, 0.53.2 и далее**; новая minor-версия не нужна для каждого исправления.

Это текущий backlog. Старый продуктовый план сохранён в [архиве](archive/roadmap-before-2026-10-07.md), подробности облачного хранения — в [DATA_PLAN.md](DATA_PLAN.md). Подтверждённых P0 в аудите нет; security hardening и подтверждённые сбои данных остаются обязательными независимо от оценки трудозатрат.

| ID | Приоритет | Работа и приёмка | Состояние |
|---|---|---|---|
| F05 | P1 | Ошибка записи recommendation log сохраняет HTTP-ответ и попадает в diagnostics; запись восстанавливается после устранения ошибки | Слито: [PR #100](https://github.com/makquella/dota-ai-coach/pull/100), 0.53.1 |
| F09 | P1 | Короткий AGENTS, тонкий CLAUDE adapter, явные targeted checks вместо глобальных hooks; справочные сведения сохранены | Слито: [PR #101](https://github.com/makquella/dota-ai-coach/pull/101) |
| F08 | P1 | Проверить актуальные advisory ranges; обновить совместимые Electron/updater/build/Wrangler зависимости; clean install, unit suites, Windows build/smoke | Слито: [PR #102](https://github.com/makquella/dota-ai-coach/pull/102), 0.53.2; остаточный build-only advisory описан в DEPENDENCIES.md |
| F07 | P1 | Зафиксировать Python runtime/dev/build зависимости и tools; единый путь установки в CI и packaging | Слито: [PR #103](https://github.com/makquella/dota-ai-coach/pull/103), 0.53.3; type baseline относится к F14 |
| F01 | P1 | Durable pending finish → idempotent DB save → ack; restart и write-failure тесты сохраняют timeline | Подготовлено в 0.53.4; протокол и ограничения — [MATCH_RECOVERY.md](MATCH_RECOVERY.md) |
| F02 | P1 | Дедупликация running jobs, stop/join с deadline, безопасный lifetime store; настоящие threads + Events | Подготовлено в 0.53.5; протокол и границы — [JOB_QUEUE_LIFECYCLE.md](JOB_QUEUE_LIFECYCLE.md) |
| F03 | P1 | Валидация backup до записи и одна transaction с account linking; rollback на сбое, восстановление повреждённого cache | Подготовлено в 0.53.6; формат и гарантии — [HISTORY_BACKUP.md](HISTORY_BACKUP.md) |
| F06 | P1 | Отдельные control/GSI tokens, Origin/Host checks и bounded body; реальный Dota config и launcher smoke совместимы | Подготовлено в 0.53.7; протокол и manual debug — [LOCAL_API_SECURITY.md](LOCAL_API_SECURITY.md) |
| F04 | P1 | Связать AI числа с метрикой и источником; начать с трёх findings, запретить metric swaps | Первый slice в 0.53.13: match combat totals + typed refs/UI; другие метрики, findings/time slices и career остаются — [AI_COUNTER_EVIDENCE.md](AI_COUNTER_EVIDENCE.md) |
| F10 | P2 | Согласованный runtime snapshot и ownership MatchMemory; concurrent publish/read/reset без disk/network под lock | Не реализовано |
| F11 | P2 | Atomic conditional transfer claims и conflict-safe insert; migrations + concurrency на local D1 | Подготовлено в 0.53.11; реальные D1 проверки — [TRANSFER_ATOMICITY.md](TRANSFER_ATOMICITY.md) |
| F12 | P2 | DTO/contract tests важных player/detail/facts ответов и их JS consumers | Не реализовано |
| F13 | P2 | Извлекать jobs/locales/detail controller по одной границе с behavior/UI tests | Первый slice в 0.53.14: independent JobQueue + fresh-process/real-thread tests; UI slices остаются |
| F14 | P2 | Locked mypy + baseline и blocking checks чистых модулей; долг не растёт | Подготовлено в 0.53.9; 226 известных ошибок, blocking gate — [TYPE_CHECKING.md](TYPE_CHECKING.md) |
| F15 | P2 | Reusable validation проверяет тот же SHA до release publish | Подготовлено в 0.53.10; протокол — [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) |
| F16 | P2 | Canonical npm syntax check, отмена superseded PR CI; meaningful-path Windows gating со стабильным required summary | Первая часть слита в #101; gating подготовлен в 0.53.12 — [WINDOWS_CI_SCOPE.md](WINDOWS_CI_SCOPE.md) |
| F17 | P2 | Trusted IPC sender/frame, navigation/popup guards, incremental CSP; реальные UI smoke checks | Подготовлено в 0.53.8; границы и smoke — [DESKTOP_SECURITY.md](DESKTOP_SECURITY.md) |

После finish/queue recovery: backup/auth как отдельные исправления с fault tests. Не ждать большого рефакторинга для подтверждённых потерь данных. Для поведения live-политики использовать sanitized role recordings и fixed-clock replay, для новых UI границ — настоящие DOM-сценарии.

Следующие продуктовые улучшения после safeguards: источники/покрытие данных в разборе, preview восстановления истории, rotating local backups, сопоставимость Progress между версиями правил. Метрики и сроки проверять на фактических данных; их наличие в плане не означает, что функции уже реализованы.

Минимальный local D1 harness для transfer создан в `services/api/test/integration/`; другие SQL paths требуют расширения проверок. Developer runner `scripts/dev.py`, portable scoped hook adapter и общий UI regression harness пока **не созданы**. До их внедрения использовать проверенные команды из [TESTING.md](TESTING.md) и [REFERENCE_COMMANDS.md](REFERENCE_COMMANDS.md). Новые helpers должны выбирать cwd и argv явно, учитывать staged/unstaged/untracked paths и не выполнять deploy, publish или платные AI вызовы.
