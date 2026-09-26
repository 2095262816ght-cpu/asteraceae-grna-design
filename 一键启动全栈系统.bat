@echo off
title Launch Asteraceae CRISPR Fullstack Platform
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_fullstack.ps1" %*
if errorlevel 1 pause
