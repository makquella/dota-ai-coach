# Sends a release installer to VirusTotal and adds the report's link to the
# release notes (`**VirusTotal:** <url>`); the site shows «Проверка VirusTotal»
# only when the notes carry the link for this installer's SHA-256.
# Used by release.yml after publishing and by virustotal.yml by hand for a
# release whose upload failed. Needs VT_API_KEY and GH_TOKEN in the environment.
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Installer
)
$ErrorActionPreference = "Stop"

if (-not $env:VT_API_KEY) { Write-Host "VT_API_KEY is not set: skipped."; exit 0 }
$file = Get-Item $Installer
$hash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
$report = "https://www.virustotal.com/gui/file/$hash"

$notes = (gh release view $Tag --json body --jq .body) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "gh release view failed with exit code $LASTEXITCODE" }
if ($notes -like "*$report*") { Write-Host "The notes already link $report."; exit 0 }

# Files over 32 MB go to a one-time upload URL. curl builds the multipart body:
# VirusTotal refuses the one PowerShell's -Form writes («Malformed multipart body»).
$headers = @{ "x-apikey" = $env:VT_API_KEY }
$uploadUrl = (Invoke-RestMethod -Uri "https://www.virustotal.com/api/v3/files/upload_url" -Headers $headers).data
$raw = & curl.exe --silent --show-error --fail-with-body --max-time 900 `
    -H "x-apikey: $($env:VT_API_KEY)" -F "file=@$($file.FullName)" $uploadUrl
if ($LASTEXITCODE -ne 0) { throw "VirusTotal upload failed (curl exit $LASTEXITCODE): $raw" }
$answer = ($raw -join "`n") | ConvertFrom-Json
if (-not $answer.data.id) { throw "VirusTotal did not accept the file: $raw" }
Write-Host "VirusTotal: $report (analysis $($answer.data.id))"

$notesFile = Join-Path ([System.IO.Path]::GetTempPath()) "release-notes-$Tag.md"
Set-Content -Path $notesFile -Encoding utf8 -Value "$notes`n`n**VirusTotal:** $report"
gh release edit $Tag --notes-file $notesFile
if ($LASTEXITCODE -ne 0) { throw "gh release edit failed with exit code $LASTEXITCODE" }
