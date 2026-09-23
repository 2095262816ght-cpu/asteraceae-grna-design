@echo off
chcp 65001 >nul
title 莴苣基因编辑 gRNA 设计与脱靶评估工具
cd /d "%~dp0"
echo ======================================================================
echo  正在启动 莴苣基因编辑 gRNA 设计与脱靶评估工具 (Streamlit Web Demo)...
echo ======================================================================
echo 正在自动检测 Python 与 Conda 环境...

set "CRISPR_PY="
for %%P in (
    "%~dp0..\..\envs\crispr\python.exe"
    "%USERPROFILE%\miniconda3\envs\crispr\python.exe"
    "%USERPROFILE%\anaconda3\envs\crispr\python.exe"
    "C:\miniconda3\envs\crispr\python.exe"
    "C:\anaconda3\envs\crispr\python.exe"
    "C:\ProgramData\miniconda3\envs\crispr\python.exe"
    "C:\ProgramData\anaconda3\envs\crispr\python.exe"
    "D:\Miniconda\envs\crispr\python.exe"
    "D:\miniconda3\envs\crispr\python.exe"
    "D:\anaconda3\envs\crispr\python.exe"
) do (
    if exist "%%~fP" if not defined CRISPR_PY set "CRISPR_PY=%%~fP"
)

if defined CRISPR_PY (
    echo [OK] 找到实时打分引擎: %CRISPR_PY%
    set "CRISPR_PYTHON=%CRISPR_PY%"
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
