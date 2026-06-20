# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None

BACKEND_DIR = Path(SPECPATH).parent
REPO_ROOT = BACKEND_DIR.parent


def data_dir(source: Path, destination: str):
    return [(str(source), destination)] if source.exists() else []


datas = []
datas += data_dir(REPO_ROOT / "data" / "heroes", "data/heroes")
datas += data_dir(REPO_ROOT / "data" / "meta", "data/meta")
datas += data_dir(REPO_ROOT / "data" / "knowledge_base", "data/knowledge_base")

hiddenimports = []
for package in (
    "app",
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "pydantic_core",
    "anyio",
    "sniffio",
):
    hiddenimports += collect_submodules(package)

a = Analysis(
    [
        str(BACKEND_DIR / "packaging" / "backend_server.py"),
        str(BACKEND_DIR / "packaging" / "demo_playback.py"),
    ],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

backend_exe = EXE(
    pyz,
    [a.scripts[0]],
    [],
    exclude_binaries=True,
    name="dota-ai-coach-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

demo_exe = EXE(
    pyz,
    [a.scripts[1]],
    [],
    exclude_binaries=True,
    name="dota-ai-coach-demo-playback",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    backend_exe,
    demo_exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="dota-ai-coach-backend",
)
