@echo off
title Build CRISPR Offline Package
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_offline_package.ps1"
if errorlevel 1 pause
