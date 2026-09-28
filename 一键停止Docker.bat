@echo off
title Stop CRISPR Docker Containers
cd /d "%~dp0"
docker compose down
echo.
echo Containers stopped.
pause
