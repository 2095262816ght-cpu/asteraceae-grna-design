@echo off
title Import CRISPR Docker Images and Start
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0import_offline_package.ps1"
if errorlevel 1 pause
