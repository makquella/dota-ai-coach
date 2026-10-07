# Проверка типов без роста долга

F14 в 0.53.9 заменяет `mypy app || true` на обязательный `scripts/check_types.py`. Используется **mypy 2.4.0** из hash-locked `requirements-dev.txt` и Python target **3.11** из backend config. Проверяется весь `app/`, включая новые модули. Сам checker дополнительно проходит `mypy --strict` без baseline.

Текущий baseline содержит **226 ошибок в 31 файле**, сгруппированных в 103 уникальных записи. Это известный долг, а не исправленные ошибки. Запись включает путь, сообщение, error code и число повторений. Номера строк/колонок и лишние пробелы форматирования не участвуют в сравнении, поэтому обычные правки не требуют обновлять baseline.

## Что останавливает CI

- Новое сообщение, code или файл, а также дополнительное повторение известной ошибки. Одинаковое общее число ошибок не скрывает замену одной ошибки другой.
- Ошибка в чистом модуле. В baseline явно объявлены `diagnostics`, `local_api_auth`, `local_api_security`, `player_store`, `signal_capabilities`, `storage_json`; для них нет allowances. Все остальные модули без известных ошибок тоже проверяются без allowances.
- Устаревшее allowance после исправления ошибки: его нужно удалить из baseline, чтобы последующий возврат ошибки считался регрессией.
- Несовпадение версии mypy/target, неверный baseline, исчезнувший clean module, нераспознанный error format, failure/timeout самого mypy.

Настройки mypy, включая текущие `check_untyped_defs` и `ignore_missing_imports`, сохранены. Gate ограничивает диагностику, которую обнаруживает этот checker; он не превращает старые `Any` и неаннотированные границы в строгие типы. Числовая/фактическая валидность AI-ответов относится к F04, runtime failures и consumer contracts — к функциональным тестам.

## Команды

Из `backend/` с существующим venv:

```bash
python ../scripts/check_types.py
python -m mypy --strict ../scripts/check_types.py
python -m pytest tests/test_type_gate.py
```

Команду checker можно запускать из другого cwd: пути и cwd mypy выбираются явно относительно script. `--backend-dir` и `--baseline` используются для изолированных fixtures или другого checkout. Checker запускает mypy тем же `sys.executable`, без shell.

После исправления существующих type errors:

```bash
python ../scripts/check_types.py --prune-baseline
git diff -- type-baseline.json
python ../scripts/check_types.py
```

Prune работает только если новых ошибок нет, и только удаляет разрешения на исчезнувшие ошибки. Новые allowances автоматически не создаются; при отказе baseline остаётся прежним. Сокращение baseline коммитится вместе с исправлением и проходит review. Обновление закреплённого mypy требует отдельного согласованного изменения lockfile, tool metadata и разбора diagnostic diff; обычный prune не обходится с версией другого checker.

CI проверяет lint/format самого script, blocking gate, strict checker, затем pytest. Интеграционные тесты запускают настоящий установленный mypy через CLI на временных модулях: line shifts, repeated errors, message/source swaps при прежнем total, новый модуль, исправление/prune/возврат ошибки и неверный baseline. Эти fixtures не меняют рабочий `app/` и не отключают реальные проверки.
