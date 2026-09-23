@echo off
chcp 65001 >nul
cd /d "%~dp0cs_pipeline"
call "%~dp0cs_pipeline\deploy_demo_cn.bat"
