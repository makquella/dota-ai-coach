<#
.SYNOPSIS
  One-command Windows build of Wardly.

.DESCRIPTION
  1. Creates backend\.venv-build (if missing) and installs the hashed backend\requirements-build.txt.
  2. Builds the backend with PyInstaller (backend\dist\dota-ai-coach-backend\).
  3. Installs the Electron app dependencies (npm ci) in frontend\launcher.
  4. Packs the Electron app with electron-builder and produces the NSIS installer:
       frontend\launcher\dist\Wardly-Setup-<version>.exe
       frontend\launcher\dist\win-unpacked\Wardly.exe

  Code signing is optional and off unless configured by env (see
  docs/PACKAGING_WINDOWS.md, "Code signing"):
    Azure Artifact Signing: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
      AZURE_SIGNING_ENDPOINT, AZURE_SIGNING_ACCOUNT, AZURE_SIGNING_PROFILE, SIGN_PUBLISHER_NAME
    or a certificate for signtool: CSC_LINK (+ CSC_KEY_PASSWORD)
  electron-builder then signs Wardly.exe, the bundled backend exe and the installer.

.PARAMETER Python
  Python 3.11+ used to create backend\.venv-build when it does not exist yet.

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
$VenvPython = Join-Path $BackendDir ".venv-build\Scripts\python.exe"
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

$SignArgs = @()
$AzureSigning = $env:AZURE_SIGNING_ENDPOINT -and $env:AZURE_SIGNING_ACCOUNT -and `
  $env:AZURE_SIGNING_PROFILE -and $env:SIGN_PUBLISHER_NAME
if ($AzureSigning) {
  # Azure Artifact Signing; Entra ID credentials come from AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET.
  $SignArgs = @(
    "-c.win.azureSignOptions.endpoint=$($env:AZURE_SIGNING_ENDPOINT)",
    "-c.win.azureSignOptions.codeSigningAccountName=$($env:AZURE_SIGNING_ACCOUNT)",
    "-c.win.azureSignOptions.certificateProfileName=$($env:AZURE_SIGNING_PROFILE)",
    "-c.win.azureSignOptions.publisherName=$($env:SIGN_PUBLISHER_NAME)"
  )
  Write-Host "Code signing: Azure Artifact Signing ($($env:SIGN_PUBLISHER_NAME))"
}
elseif ($env:CSC_LINK) {
  Write-Host "Code signing: certificate from CSC_LINK"
}
else {
  # No signing configured: do not let electron-builder search for a certificate.
  $env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
  Write-Host "Code signing: off (unsigned build)"
}

if (-not $SkipBackend) {
  Push-Location $BackendDir
  try {
    if (-not (Test-Path $VenvPython)) {
      Invoke-Native "Create backend\.venv-build" { & $Python -m venv .venv-build }
    }
    Invoke-Native "Install backend build requirements" {
      & $VenvPython -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r requirements-build.txt
    }
    Invoke-Native "Check backend build requirements" {
      & $VenvPython -m pip check
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
    npx --no-install electron-builder --win @targets --publish never @SignArgs
  }
}
finally {
  Pop-Location
}

$dist = Join-Path $LauncherDir "dist"
Write-Host ""
Write-Host "Build finished:" -ForegroundColor Green
Get-ChildItem $dist -Filter *.exe | ForEach-Object { Write-Host "  installer: $($_.FullName)" }
Write-Host "  app:       $(Join-Path $dist 'win-unpacked\Wardly.exe')"
