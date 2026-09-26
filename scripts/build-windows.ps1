<#
.SYNOPSIS
  One-command Windows build of Dota AI Coach.

.DESCRIPTION
  1. Creates backend\.venv (if missing) and installs backend\requirements-build.txt.
  2. Builds the backend with PyInstaller (backend\dist\dota-ai-coach-backend\).
  3. Installs the Electron app dependencies (npm ci) in frontend\launcher.
  4. Packs the Electron app with electron-builder and produces the NSIS installer:
       frontend\launcher\dist\DotaAICoach-Setup-<version>.exe
       frontend\launcher\dist\win-unpacked\DotaAICoach.exe

.PARAMETER Python
  Python 3.11+ used to create backend\.venv when it does not exist yet.

.PARAMETER Portable
  Also build the optional single-file portable exe.

.PARAMETER SkipBackend
  Reuse an existing backend\dist build (frontend-only rebuild).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
#>
[CmdletBinding()]
param(
  [string]$Python = "python",
  [switch]$Portable,
  [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$LauncherDir = Join-Path $RepoRoot "frontend\launcher"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$BackendExe = Join-Path $BackendDir "dist\dota-ai-coach-backend\dota-ai-coach-backend.exe"

function Invoke-Native {
  param([string]$Title, [scriptblock]$Command)
  Write-Host ""
  Write-Host "==> $Title" -ForegroundColor Cyan
  $global:LASTEXITCODE = 0
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Title failed with exit code $LASTEXITCODE"
  }
}

if (-not $env:CSC_LINK) {
  # No signing certificate configured: do not let electron-builder search for one.
  $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
}

if (-not $SkipBackend) {
  Push-Location $BackendDir
  try {
    if (-not (Test-Path $VenvPython)) {
      Invoke-Native "Create backend\.venv" { & $Python -m venv .venv }
    }
    Invoke-Native "Install backend build requirements" {
      & $VenvPython -m pip install --disable-pip-version-check -r requirements-build.txt
    }
    foreach ($dir in @("build", "dist")) {
      if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
    }
    Invoke-Native "Build backend with PyInstaller" {
      & $VenvPython -m PyInstaller --noconfirm --clean packaging\dota_ai_coach_backend.spec
    }
  }
  finally {
    Pop-Location
  }
}

if (-not (Test-Path $BackendExe)) {
  throw "Backend executable was not found: $BackendExe"
}

Push-Location $LauncherDir
try {
  Invoke-Native "Install Electron app dependencies" { npm ci --no-audit --no-fund }
  if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
  $targets = @("nsis")
  if ($Portable) { $targets += "portable" }
  Invoke-Native "Build Electron app + installer ($($targets -join ', '))" {
    npx --no-install electron-builder --win @targets --publish never
  }
}
finally {
  Pop-Location
}

$dist = Join-Path $LauncherDir "dist"
Write-Host ""
Write-Host "Build finished:" -ForegroundColor Green
Get-ChildItem $dist -Filter *.exe | ForEach-Object { Write-Host "  installer: $($_.FullName)" }
Write-Host "  app:       $(Join-Path $dist 'win-unpacked\DotaAICoach.exe')"
