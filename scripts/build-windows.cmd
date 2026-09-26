@echo off
rem One-command Windows build. See docs\PACKAGING_WINDOWS.md.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1" %*
