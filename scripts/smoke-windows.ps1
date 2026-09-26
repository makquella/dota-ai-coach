<#
.SYNOPSIS
  Smoke-tests the Windows build produced by scripts\build-windows.ps1.

.DESCRIPTION
  1. Backend exe: starts dota-ai-coach-backend.exe on a free port (the way the
     app does), checks /health and /overlay/recommendation, checks that
     writable files land in %APPDATA%\DotaAICoach, then stops it gracefully via
     stdin and expects exit code 0.
  2. App exe: runs DotaAICoach.exe --smoke-test (the app starts its bundled
     backend hidden, checks /health, stops it gracefully and exits).
  3. Fake Dota: compiles a plain window named dota2.exe, starts it and repeats
     step 2; the Dota watcher must find that window and the overlay must be
     placed inside it (multi-monitor placement, helper struct marshalling).
  4. Auto-update files: dist\latest.yml and resources\app-update.yml exist.
  5. Installer: installs silently and repeats step 2 with the installed exe.
#>
[CmdletBinding()]
param(
  [int]$TimeoutSeconds = 90,
  [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendExe = Join-Path $RepoRoot "backend\dist\dota-ai-coach-backend\dota-ai-coach-backend.exe"
$DistDir = Join-Path $RepoRoot "frontend\launcher\dist"
$AppExe = Join-Path $DistDir "win-unpacked\DotaAICoach.exe"
$WorkDir = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$UserDataDir = Join-Path $env:APPDATA "DotaAICoach"

function Get-FreePort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try { return $listener.LocalEndpoint.Port } finally { $listener.Stop() }
}

function Assert-True([bool]$Condition, [string]$Message) {
  if (-not $Condition) { throw "FAIL: $Message" }
  Write-Host "PASS: $Message" -ForegroundColor Green
}

function Assert-NoBackendLeft {
  Start-Sleep -Seconds 2
  $left = @(Get-Process -Name "dota-ai-coach-backend" -ErrorAction SilentlyContinue)
  Assert-True ($left.Count -eq 0) "no dota-ai-coach-backend process left running"
}

function Test-BackendExe {
  Write-Host "`n==> Backend exe: $BackendExe" -ForegroundColor Cyan
  Assert-True (Test-Path $BackendExe) "backend exe exists"

  $port = Get-FreePort
  $psi = [System.Diagnostics.ProcessStartInfo]::new($BackendExe)
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.RedirectStandardInput = $true
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.WorkingDirectory = Split-Path -Parent $BackendExe
  $psi.Environment["DOTA_AI_BACKEND_PORT"] = "$port"
  $psi.Environment["DOTA_AI_BACKEND_STDIN_CONTROL"] = "1"
  $proc = [System.Diagnostics.Process]::Start($psi)
  $stdout = $proc.StandardOutput.ReadToEndAsync()
  $stderr = $proc.StandardError.ReadToEndAsync()
  $base = "http://127.0.0.1:$port"

  try {
    $healthy = $false
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline -and -not $proc.HasExited) {
      try {
        $health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 2
        if ($health.status -eq "ok") { $healthy = $true; break }
      } catch {
        Start-Sleep -Milliseconds 500
      }
    }
    Assert-True $healthy "backend answers $base/health"

    $overlay = Invoke-RestMethod -Uri "$base/overlay/recommendation" -TimeoutSec 5
    Assert-True ([bool]$overlay.status) "/overlay/recommendation returns status '$($overlay.status)'"

    $recording = Invoke-RestMethod -Method Post -Uri "$base/session-recording/start" -TimeoutSec 5
    $null = Invoke-RestMethod -Method Post -Uri "$base/session-recording/stop" -TimeoutSec 5
    $sessionDir = [string]$recording.session_dir
    Assert-True ($sessionDir.StartsWith($UserDataDir, [System.StringComparison]::OrdinalIgnoreCase)) "session records go to $UserDataDir ($sessionDir)"
    Assert-True (Test-Path $sessionDir) "session record folder was created"

    $proc.StandardInput.WriteLine("shutdown")
    $proc.StandardInput.Close()
    $exited = $proc.WaitForExit(15000)
    Assert-True $exited "backend exits after the stdin shutdown command"
    Assert-True ($proc.ExitCode -eq 0) "backend exit code is 0 (got $($proc.ExitCode))"
  }
  finally {
    if (-not $proc.HasExited) { $proc.Kill() }
    $proc.WaitForExit()
    Write-Host "--- backend stdout ---"; Write-Host $stdout.Result
    Write-Host "--- backend stderr ---"; Write-Host $stderr.Result
  }
}

function Test-AppExe([string]$Exe, [string]$Label) {
  Write-Host "`n==> App smoke test ($Label): $Exe" -ForegroundColor Cyan
  Assert-True (Test-Path $Exe) "$Label exe exists"

  $resultPath = Join-Path $WorkDir "smoke-$Label.json"
  if (Test-Path $resultPath) { Remove-Item $resultPath }
  $proc = Start-Process -FilePath $Exe -ArgumentList "--smoke-test=`"$resultPath`"" -PassThru
  $null = $proc.Handle  # keeps ExitCode readable after exit
  if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    # Clean up the app and the backend it owns so later steps start from a clean state.
    $proc.Kill()
    $null = $proc.WaitForExit(10000)
    Get-Process -Name "dota-ai-coach-backend" -ErrorAction SilentlyContinue | Stop-Process -Force
    throw "FAIL: $Label did not finish the smoke test within $TimeoutSeconds s"
  }
  Assert-True (Test-Path $resultPath) "$Label wrote $resultPath"
  $result = Get-Content $resultPath -Raw | ConvertFrom-Json
  foreach ($step in $result.steps) {
    Write-Host ("  {0} {1} {2}" -f $(if ($step.ok) { "ok  " } else { "FAIL" }), $step.name, $step.detail)
  }
  if (-not $result.ok) { Write-Host $result.logs }
  Assert-True ([bool]$result.ok) "$Label smoke test passed (backend port $($result.port))"
  Assert-True ($proc.ExitCode -eq 0) "$Label exit code is 0 (got $($proc.ExitCode))"
  Assert-NoBackendLeft
}

function New-FakeDota {
  # A plain WinForms window called dota2.exe, built with the .NET Framework
  # compiler that ships with Windows (no SDK needed).
  $dir = Join-Path $WorkDir "fake-dota"
  $exe = Join-Path $dir "dota2.exe"
  if (Test-Path $exe) { return $exe }
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $source = Join-Path $dir "FakeDota.cs"
  Set-Content -Path $source -Encoding UTF8 -Value @'
using System;
using System.Drawing;
using System.Windows.Forms;

public static class FakeDota {
  [STAThread]
  public static void Main() {
    var form = new Form {
      Text = "Dota 2",
      StartPosition = FormStartPosition.Manual,
      Location = new Point(40, 40),
      Size = new Size(900, 600)
    };
    Application.Run(form);
  }
}
'@
  $csc = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
  Assert-True (Test-Path $csc) "C# compiler found for the fake dota2.exe"
  & $csc /nologo /target:winexe "/out:$exe" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll $source
  Assert-True ($LASTEXITCODE -eq 0 -and (Test-Path $exe)) "fake dota2.exe compiled"
  return $exe
}

function Test-AppWithFakeDota {
  $fake = Start-Process -FilePath (New-FakeDota) -PassThru
  try {
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
      $fake.Refresh()
      if ($fake.MainWindowHandle -ne [IntPtr]::Zero) { break }
      Start-Sleep -Milliseconds 250
    }
    Assert-True ($fake.MainWindowHandle -ne [IntPtr]::Zero) "fake dota2.exe shows a window"
    $env:DOTA_AI_SMOKE_FAKE_DOTA = "1"
    Test-AppExe $AppExe "fake-dota"
  }
  finally {
    Remove-Item Env:\DOTA_AI_SMOKE_FAKE_DOTA -ErrorAction SilentlyContinue
    if (-not $fake.HasExited) { $fake.Kill() }
  }
}

function Test-UpdateFiles {
  Write-Host "`n==> Auto-update files" -ForegroundColor Cyan
  $latest = Join-Path $DistDir "latest.yml"
  Assert-True (Test-Path $latest) "dist\latest.yml exists (electron-updater feed)"
  $feed = Get-Content $latest -Raw
  $installer = Get-ChildItem $DistDir -Filter "DotaAICoach-Setup-*.exe" | Select-Object -First 1
  Assert-True ($feed.Contains($installer.Name)) "latest.yml points at $($installer.Name)"
  $appUpdate = Join-Path $DistDir "win-unpacked\resources\app-update.yml"
  Assert-True (Test-Path $appUpdate) "resources\app-update.yml exists"
  $config = Get-Content $appUpdate -Raw
  Assert-True ($config -match "provider:\s*github" -and $config -match "repo:\s*dota-ai-coach") "app-update.yml uses GitHub releases"
}

function Test-Installer {
  $installer = Get-ChildItem $DistDir -Filter "DotaAICoach-Setup-*.exe" | Select-Object -First 1
  Assert-True ($null -ne $installer) "NSIS installer exists in $DistDir"
  Write-Host "`n==> Silent install: $($installer.FullName)" -ForegroundColor Cyan
  $proc = Start-Process -FilePath $installer.FullName -ArgumentList "/S" -PassThru -Wait
  Assert-True ($proc.ExitCode -eq 0) "installer exit code is 0 (got $($proc.ExitCode))"

  $installed = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs") -Recurse -Filter "DotaAICoach.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
  Assert-True ($null -ne $installed) "installed DotaAICoach.exe found under %LOCALAPPDATA%\Programs"
  # The one-click installer may start the app itself; stop it before the smoke run.
  Get-Process -Name "DotaAICoach" -ErrorAction SilentlyContinue | Stop-Process -Force
  Test-AppExe $installed.FullName "installed"
}

try {
  Test-BackendExe
  Assert-NoBackendLeft
  Test-AppExe $AppExe "win-unpacked"
  Test-AppWithFakeDota
  Test-UpdateFiles
  if (-not $SkipInstaller) {
    Test-Installer
  }
}
finally {
  $launcherLog = Join-Path $UserDataDir "logs\launcher.log"
  if (Test-Path $launcherLog) { Copy-Item $launcherLog (Join-Path $WorkDir "launcher.log") -Force }
}
Write-Host "`nAll Windows smoke tests passed." -ForegroundColor Green
