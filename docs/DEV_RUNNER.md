# Portable developer runner (0.53.42)

`python scripts/dev.py` chooses explicit cwd/argv and uses the existing backend
venv (`Scripts/python.exe` or `bin/python`). Checks never install dependencies,
start an app, call paid AI, deploy or publish. No shell interpolation: npm runs
through Node and its actual `npm-cli.js`, including on Windows. Review a plan:

```text
python scripts/dev.py check --changed --dry-run
python scripts/dev.py check --changed
python scripts/dev.py check --changed --base main
python scripts/dev.py check --scope live
python scripts/dev.py check --scope desktop --scope history
python scripts/dev.py lint --changed
python scripts/dev.py format --changed
python scripts/dev.py typecheck
python scripts/dev.py test --target backend/tests/test_match_notes.py
python scripts/dev.py test --scope worker --integration
python scripts/dev.py check --full
```

Changed selection unions staged, unstaged and untracked paths using NUL-delimited
Git output. `--base` adds committed changes relative to a verified commit. Renames
include both names and deletions select their former consumers. Ignored runtime
artifacts remain ignored. The JSON plan lists paths, profiles, exact commands and
reasons. An empty tree runs only whitespace validation.

`live`, `history`, `ai`, `desktop`, `worker`, `site`, `tooling` and full `backend`
profiles use the explicit map in the runner and [TESTING.md](TESTING.md). Shared
API/config/schema/store/main/preload inputs expand checks. Unknown backend paths
use the whole backend; unknown root/build/workflow inputs are conservative.
New changed JS files receive syntax checks alongside canonical desktop checks.
Python lint/format-check covers existing selected paths; deleted sources still
select tests. Unknown tests use the full backend. Python formatting changes files
only through the explicit `format` command. Full check validates the entire
backend, launcher and Worker (including genuine local D1), type gate, generated
site/changelog and versions. These are consumer profiles, not a claim of perfect
static dependency inference; actual UI/replay acceptance remains task-specific.

`bump_version.py --check` is read-only. It reads both backend values via Python AST,
package/lock/root versions via JSON, executes the actual RU/EN update module with
Node, and requires current/latest copy and bilingual notes. New copy and analysis
cache versions stay deliberate. CI runs this gate plus lint/strict types for the
runner; it cannot silently accept a forgotten root version or locale entry.

Setup/run/build are explicit separate actions:

```text
python scripts/dev.py setup --python <Python-3.11+-executable>
python scripts/dev.py setup --scope worker
python scripts/dev.py dev
python scripts/dev.py dev --scope backend
python scripts/dev.py build
python scripts/dev.py build --skip-backend
python scripts/dev.py check --full --package
```

Setup creates a missing venv and installs hashed locked dev dependencies / npm ci;
Worker is opt-in. Default dev starts the launcher, which owns its backend. Standalone
backend requires its scope. Build/package require actual Windows; `--skip-backend`
requires a valid previous backend build. No command calls release publication.
Source Electron smoke remains the explicit command in TESTING; Linux headless smoke
does not replace Windows installer validation or actual Dota GSI integration.

The optional `scripts/check_hook.py edit` reads `tool_input.file_path` from JSON
stdin, confines it to a real repository file and lints only an edited Python file
under backend/scripts. `--format` explicitly enables that file's formatting. JS/docs
trigger no backend-wide check. `stop` respects `stop_hook_active` and gives a hint
when the current changed tree lacks a successful receipt; it never runs full tests.
Hooks remain disabled in `.claude/settings.json`; installing them is optional.

A successful `check --changed` writes an atomic local temporary receipt only if
source contents and index status remain unchanged during checks. It contains a
fingerprint and successful profiles, without source text. Stop compares the current
tree and needed profiles before suppressing repeated hints. This is convenience,
not a security/approval boundary or evidence for a different tool environment.
A failed or dry-run plan never creates a successful receipt. Scope/code changes
invalidate it; the receipt is not committed or uploaded.
