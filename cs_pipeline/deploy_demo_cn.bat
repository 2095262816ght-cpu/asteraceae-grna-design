@echo off
chcp 65001 >nul
title 菊科菊苣族 gRNA 设计工具 — 一键部署 (国内镜像版)
cd /d "%~dp0"
echo ======================================================================
echo  正在启动一键部署程序（清华镜像加速，无需梯子）...
echo ======================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_demo_cn.ps1"
if errorlevel 1 (
    echo.
    echo 部署过程中遇到问题，请查看上方提示信息。
    pause
)
