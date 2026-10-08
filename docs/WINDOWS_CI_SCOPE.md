# Windows CI: scope и стабильный статус

F16 в 0.53.12 сохраняет проверки backend/frontend и отмену superseded PR CI. Дорогая Windows-сборка запускается по изменениям, которые могут затронуть installer, с отдельным стабильным обязательным summary.

## Выбор source и paths

Read-only `changes` job checkout того же immutable SHA, что остальные jobs, с history для base. Для PR используется frozen `pull_request.base.sha`, для push — `before`. `windows_checks.py` проверяет HEAD/tracked source и сравнивает эти commits через `git diff --name-only --no-renames -z`. Rename показывает и удалённый source, поэтому перемещение packaged файла в docs не скрывает изменение.

Исключаются только известные деревья вне installer: `docs/`, `site/`, `services/api/`, `.agents/`, `.claude/`, root `AGENTS.md`/`CLAUDE.md` и API workflow. Worker имеет собственный API workflow с unit/real D1/bundle checks. Все остальные paths, включая backend, launcher, runtime data, README (он входит в installer), dependencies, Windows scripts, shared CI/release workflows и неизвестные файлы, требуют Windows. Version-only изменения packaged files тоже требуют сборки.

Без usable base, при первом push или недоступном commit выбирается Windows. Неверный source/dirty tracked files и ошибки scope job не превращаются в skip. Pure docs/site/Worker changes продолжают проходить backend/frontend CI; это исправление сокращает только Windows target.

## Required summary

Actual build выполняет `windows-build` job с прежними PyInstaller/Electron/NSIS, smoke, source verification и installer/log artifacts. `windows-package` теперь summary на Ubuntu с **тем же существующим check name**: `Windows package (PyInstaller + NSIS, /health smoke)`.

Summary зависит от `changes` и `windows-build`, выполняется с `always()` и принимает только:

- успешный scope и успешную Windows-сборку;
- успешный scope и skip, когда desktop paths не менялись;
- успешный scope и skip от reusable Release caller, который выполняет свою signed Windows-сборку после validation, как предусмотрено F15.

Failure/cancellation/skipped scope, failure/cancellation build или необоснованный skip дают failure стабильного статуса. Backend/frontend check names сохраняются. Existing branch protections не нужно менять на имя внутреннего build job. Новый summary не заменяет отдельно обязательные backend/frontend checks.

## Проверки

`tests/test_windows_checks.py` вызывает CLI и настоящие временные Git repositories: Unicode/space filenames, non-desktop paths, unknown input, rename из backend в docs, missing/unavailable base и матрицу success/failure/cancel/skip. Workflow contract проверяет прежний required name, dependency graph и full history; actionlint проверяет expressions. Helper проходит strict mypy без baseline.

```bash
# из backend/
python -m pytest tests/test_windows_checks.py tests/test_release_validation.py
python -m mypy --strict ../scripts/windows_checks.py
```

PR самого исправления меняет packaged version и shared CI, поэтому обязан выполнить настоящую Windows-сборку. Docs-only skip проверяется CLI/Git cases; release publish не запускается при этой разработке. При добавлении нового packaged дерева пересмотреть exclusions и manifest; unknown paths уже выбираются консервативно.
