@echo off
chcp 65001 >nul
title 莴苣基因编辑 gRNA 设计与脱靶评估工具
cd /d "%~dp0"
echo ======================================================================
echo  正在启动 莴苣基因编辑 gRNA 设计与脱靶评估工具 (Streamlit 基准轨 - 端口 8501)...
echo  [提示] 如需使用全新 React 19 + FastAPI 现代化全栈系统，
echo         请双击运行根目录下的: 一键启动全栈系统.bat (端口 5173 / 8000)
echo ======================================================================
echo 正在自动检测 Python 与 Conda 环境...

set "CRISPR_PYTHON="
if exist "%~dp0..\..\envs\crispr\python.exe" set "CRISPR_PYTHON=%~dp0..\..\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "%USERPROFILE%\miniconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=%USERPROFILE%\miniconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "%USERPROFILE%\anaconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=%USERPROFILE%\anaconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "C:\miniconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=C:\miniconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "C:\anaconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=C:\anaconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "C:\ProgramData\miniconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=C:\ProgramData\miniconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "C:\ProgramData\anaconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=C:\ProgramData\anaconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "D:\Miniconda\envs\crispr\python.exe" set "CRISPR_PYTHON=D:\Miniconda\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "D:\miniconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=D:\miniconda3\envs\crispr\python.exe"
if not defined CRISPR_PYTHON if exist "D:\anaconda3\envs\crispr\python.exe" set "CRISPR_PYTHON=D:\anaconda3\envs\crispr\python.exe"

if defined CRISPR_PYTHON (
    echo [OK] 找到实时打分引擎: %CRISPR_PYTHON%
) else (
    echo [提示] 未找到独立 crispr 环境，Tab2 实时打分将使用默认 python
)

call conda activate grna-demo 2>nul
if errorlevel 1 (
    echo 正在通过 conda run 启动 Streamlit...
    conda run -n grna-demo streamlit run app/app.py
) else (
    streamlit run app/app.py
)
if errorlevel 1 (
    echo.
    echo 启动失败，请先运行 一键部署_国内源.bat 安装所需环境。
    pause
)
