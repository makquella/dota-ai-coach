# Windows CI: scope і стабільний статус

F16 у 0.53.12 зберігає перевірки backend/frontend і скасування superseded PR CI. Дорога Windows-збірка запускається за змінами, що можуть зачепити installer, з окремим стабільним обов'язковим summary.

## Вибір source і paths

Read-only `changes` job checkout того самого immutable SHA, що й інші jobs, з history для base. Для PR використовується frozen `pull_request.base.sha`, для push — `before`. `windows_checks.py` перевіряє HEAD/tracked source і порівнює ці commits через `git diff --name-only --no-renames -z`. Rename показує й видалений source, тому переміщення packaged файлу в docs не приховує зміни.

Виключаються лише відомі дерева поза installer: `docs/`, `site/`, `services/api/`, `.agents/`, `.claude/`, root `AGENTS.md`/`CLAUDE.md` і API workflow. Worker має власний API workflow з unit/real D1/bundle checks. Усі інші paths, зокрема backend, launcher, runtime data, README (він входить до installer), dependencies, Windows scripts, shared CI/release workflows і невідомі файли, потребують Windows. Version-only зміни packaged files теж потребують збирання.

Без usable base, під час першого push чи за недоступного commit вибирається Windows. Хибний source/dirty tracked files і помилки scope job не перетворюються на skip. Pure docs/site/Worker changes і далі проходять backend/frontend CI; це виправлення скорочує лише Windows target.

## Required summary

Actual build виконує `windows-build` job з попередніми PyInstaller/Electron/NSIS, smoke, source verification й installer/log artifacts. `windows-package` тепер summary на Ubuntu з **тією самою наявною check name**: `Windows package (PyInstaller + NSIS, /health smoke)`.

Summary залежить від `changes` і `windows-build`, виконується з `always()` і приймає лише:

- успішний scope й успішну Windows-збірку;
- успішний scope й skip, коли desktop paths не змінювалися;
- успішний scope й skip від reusable Release caller, який виконує свою signed Windows-збірку після validation, як передбачено F15.

Failure/cancellation/skipped scope, failure/cancellation build чи необґрунтований skip дають failure стабільного статусу. Backend/frontend check names зберігаються. Existing branch protections не треба змінювати на ім'я внутрішнього build job. Новий summary не замінює окремо обов'язкових backend/frontend checks.

## Перевірки

`tests/test_windows_checks.py` викликає CLI і справжні тимчасові Git repositories: Unicode/space filenames, non-desktop paths, unknown input, rename з backend у docs, missing/unavailable base і матрицю success/failure/cancel/skip. Workflow contract перевіряє попереднє required name, dependency graph і full history; actionlint перевіряє expressions. Helper проходить strict mypy без baseline.

```bash
# з backend/
python -m pytest tests/test_windows_checks.py tests/test_release_validation.py
python -m mypy --strict ../scripts/windows_checks.py
```

PR самого виправлення змінює packaged version і shared CI, тому мусить виконати справжню Windows-збірку. Docs-only skip перевіряється CLI/Git cases; release publish не запускається під час цієї розробки. У разі додавання нового packaged дерева переглянути exclusions і manifest; unknown paths уже вибираються консервативно.
