@echo off
rem Beast Drills -- double-click this to stop the dashboard.
rem It runs in the background with no window, so this is how you close it.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dashboard.ps1" -Stop
timeout /t 3 >nul
