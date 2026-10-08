@echo off
rem Beast Drills -- double-click this to start the dashboard.
rem
rem Windows opens a .ps1 in Notepad when you double-click it, and blocks
rem scripts by default, so this runs start_dashboard.ps1 beside it with
rem the policy relaxed for this one run only. Nothing on the PC is changed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dashboard.ps1" %*
if errorlevel 1 pause
