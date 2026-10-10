# Перевірка типів без зростання боргу

F14 у 0.53.9 замінює `mypy app || true` на обов'язковий `scripts/check_types.py`. Використовується **mypy 2.4.0** з hash-locked `requirements-dev.txt` і Python target **3.11** з backend config. Перевіряється весь `app/`, зокрема нові модулі. Сам checker додатково проходить `mypy --strict` без baseline.

Поточний baseline містить **179 помилок у 30 файлах**, згрупованих у 92 унікальні записи. У 0.53.22 typed hint boundary і narrowing item names усунули ще три помилки; allowances видалено. У 0.53.21 одноразове narrowing state/extra в live-hint path усунуло 32 помилки; allowances видалено. У 0.53.18 усунуто 11 помилок narrowing у MatchMemory й видалено відповідні allowances. У 0.53.15 виправлено повторну анотацію `items` у GSI normalizer і видалено одне allowance; вихідний F14 baseline містив 226 помилок. Решта baseline — відомий борг, а не виправлені помилки. Запис містить шлях, повідомлення, error code і кількість повторень. Номери diagnostic рядків/колонок і зайві пробіли форматування не беруть участі в порівнянні; текст повідомлення порівнюється повністю, зокрема embedded line references, якщо checker їх видає.

## Що зупиняє CI

- Нове повідомлення, code чи файл, а також додаткове повторення відомої помилки. Однакова загальна кількість помилок не приховує заміни однієї помилки іншою.
- Помилка в чистому модулі. У baseline явно оголошено `coach_evidence`, `demo_overlay_cache`, `diagnostics`, `gsi_snapshot`, `job_queue`, `live_hints`, `local_api_auth`, `local_api_security`, `match_memory`, `player_contracts`, `player_store`, `signal_capabilities`, `storage_json`; для них немає allowances. Усі інші модулі без відомих помилок теж перевіряються без allowances.
- Застаріле allowance після виправлення помилки: його треба видалити з baseline, щоб подальше повернення помилки вважалося регресією.
- Розбіжність версії mypy/target, хибний baseline, зниклий clean module, нерозпізнаний error format, failure/timeout самого mypy.

Налаштування mypy, зокрема поточні `check_untyped_defs` і `ignore_missing_imports`, збережено. Gate обмежує діагностику, яку виявляє цей checker; він не перетворює старих `Any` і неанотованих меж на строгі типи. Числова/фактична валідність AI-відповідей стосується F04, runtime failures і consumer contracts — функціональних тестів.

## Команди

З `backend/` з наявним venv:

```bash
python ../scripts/check_types.py
python -m mypy --strict ../scripts/check_types.py
python -m pytest tests/test_type_gate.py
```

Команду checker можна запускати з іншого cwd: шляхи й cwd mypy вибираються явно відносно script. `--backend-dir` і `--baseline` використовуються для ізольованих fixtures чи іншого checkout. Checker запускає mypy тим самим `sys.executable`, без shell.

Після виправлення наявних type errors:

```bash
python ../scripts/check_types.py --prune-baseline
git diff -- type-baseline.json
python ../scripts/check_types.py
```

Prune працює, лише якщо нових помилок немає, і лише видаляє дозволи на зниклі помилки. Нові allowances автоматично не створюються; у разі відмови baseline залишається попереднім. Скорочення baseline комітиться разом із виправленням і проходить review. Оновлення закріпленого mypy потребує окремої узгодженої зміни lockfile, tool metadata й розбору diagnostic diff; звичайний prune не працює з версією іншого checker.

CI перевіряє lint/format самого script, blocking gate, strict checker, потім pytest. Інтеграційні тести запускають справжній встановлений mypy через CLI на тимчасових модулях: line shifts, repeated errors, message/source swaps за попереднього total, новий модуль, виправлення/prune/повернення помилки й хибний baseline. Ці fixtures не змінюють робочого `app/` і не вимикають реальних перевірок.
