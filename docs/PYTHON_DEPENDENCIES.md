# Python dependencies

`backend/requirements*.in` declares allowed direct dependencies. The three
`requirements*.txt` files are generated, exact, hashed dependency graphs for
Python 3.11, including platform markers and Windows wheels. Do not edit the
compiled files by hand. The pinned compiler is uv 0.12.19 in the dev profile.

| Profile | Install file | Purpose |
|---|---|---|
| Runtime | `requirements.txt` | FastAPI server and offline scripts |
| Development | `requirements-dev.txt` | Runtime + pytest/httpx, Ruff, mypy and lock compiler |
| Build | `requirements-build.txt` | Runtime + PyInstaller, hooks and platform build dependencies |

Runtime and build do not include pytest or httpx. Tests and the STRATZ data
workflow use the dev profile. Runtime versions are constrained by the dev
lock when compiling runtime/build, so CI tests the libraries that packaging
uses. Runtime versions start from the already validated 0.53.2 environment;
this change does not refresh application libraries to unrelated new releases.

## Install

Create and activate a Python 3.11 venv. From `backend/`, use the same installer
for each profile, selecting its file:

```bash
python -m pip install --require-hashes --only-binary=:all: -r requirements-dev.txt
python -m pip check
```

Use `requirements.txt` for runtime-only work and `requirements-build.txt`
for packaging. Wheels-only installation avoids resolving unpinned build
dependencies for source distributions. CI and release builds use Python 3.11;
an unsupported interpreter/platform must not silently fall back to sdists.

Windows `scripts/build-windows.ps1` manages `backend/.venv-build`, separate
from the development `backend/.venv`, then runs the hashed build install and
`pip check`. Use a fresh dedicated venv when changing profiles; pip install
does not remove unrelated packages from a previously modified environment.
The lockfiles pin application/tool dependencies, not the Python distribution,
pip/bootstrap environment, OS libraries, signing credentials or external data.

## Refresh and check

With the dev venv active, from the repository root:

```bash
# Retain existing versions; regenerate metadata/hashes or add compatible inputs.
python scripts/lock_python_dependencies.py
# Refresh versions deliberately, including when .in raises a minimum version.
python scripts/lock_python_dependencies.py --upgrade
# Validate without rewriting tracked files.
python scripts/lock_python_dependencies.py --check
```

The helper chooses its cwd from its own path, invokes uv through the current
Python interpreter, compiles dev first and constrains runtime/build by it.
It prepares all outputs in a temporary directory before replacing any lock.
Metadata cache uses `UV_CACHE_DIR` when set, otherwise a temporary directory;
the helper does not require writes to the user's home directory.
It reuses version pins as temporary constraints and reads hashes from package
metadata, rather than trusting hashes copied from an existing output.
`--check` returns nonzero on drift or resolution errors. CI runs it after the exact
dev install. It needs package registry metadata; it never starts the app,
calls AI providers, publishes a release or deploys a Worker.

After a refresh: review direct and transitive changes/markers/hashes, install
all profiles in fresh venvs, run `pip check`, full backend checks and tests,
site checks, Electron smoke, and Windows build/installer smoke. Check that
runtime versions agree across profiles and test tools stay out of runtime/build.
Report mypy independently: the existing type debt remains nonblocking.

Cloud setup should install the checked-out dev lock with hashes/wheels, then
run `pip check`; the same files are used by CI, fuzzing, data workflows and
packaging. No live provider keys are needed to validate these locks.
