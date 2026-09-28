# ==============================================================================
# 菊科菊苣族 gRNA 设计工具 —— Streamlit Web 演示系统一键部署脚本（国内镜像高速版）
# ==============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " 菊科菊苣族 gRNA 设计与脱靶评估工具 — Web Demo 一键部署 (清华镜像加速)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检测 Conda
Write-Host "[1/4] 正在检测系统 Conda 环境..." -ForegroundColor Yellow
$condaCmd = Get-Command conda -ErrorAction SilentlyContinue
$condaExe = $null

if ($condaCmd) {
    $condaExe = $condaCmd.Source
} else {
    $candidatePaths = @(
        "D:\Miniconda\Scripts\conda.exe",
        "D:\Miniconda\condabin\conda.bat",
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "$env:USERPROFILE\miniconda3\condabin\conda.bat",
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\anaconda3\condabin\conda.bat",
        "C:\miniconda3\Scripts\conda.exe",
        "C:\miniconda3\condabin\conda.bat",
        "C:\anaconda3\Scripts\conda.exe",
        "C:\anaconda3\condabin\conda.bat",
        "C:\ProgramData\miniconda3\Scripts\conda.exe",
        "C:\ProgramData\miniconda3\condabin\conda.bat",
        "C:\ProgramData\anaconda3\Scripts\conda.exe",
        "C:\ProgramData\anaconda3\condabin\conda.bat"
    )
    foreach ($cand in $candidatePaths) {
        if (Test-Path $cand) {
            $condaExe = $cand
            $condaDir = Split-Path -Parent (Split-Path -Parent $cand)
            $env:PATH = "$condaDir\Scripts;$condaDir\condabin;$condaDir;$env:PATH"
            break
        }
    }
}

if (-not $condaExe) {
    Write-Host "【错误】未检测到 Conda（Miniconda 或 Anaconda）！" -ForegroundColor Red
    Write-Host "请先下载并安装 Miniconda (Windows 64位)：" -ForegroundColor Yellow
    Write-Host "清华镜像极速下载直链：" -ForegroundColor White
    Write-Host "https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Windows-x86_64.exe" -ForegroundColor Cyan
    Write-Host "安装完成后，请重新双击运行本脚本。" -ForegroundColor Yellow
    Read-Host "按回车键退出..."
    Exit 1
}

Write-Host "找到 Conda: $condaExe" -ForegroundColor Green
$PIP_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"

# 2. 检查并创建 grna-demo 环境（Web 界面）
Write-Host ""
Write-Host "[2/4] 配置 Web 界面环境 (grna-demo)..." -ForegroundColor Yellow
$envsList = conda env list
if ($envsList -match "grna-demo\s") {
    Write-Host "grna-demo 环境已存在，跳过创建，直接校验/安装依赖..." -ForegroundColor Green
} else {
    Write-Host "正在创建 grna-demo 环境 (Python 3.10)..." -ForegroundColor Cyan
    conda create -n grna-demo python=3.10 -y -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ --override-channels
    if ($LASTEXITCODE -ne 0) {
        Write-Host "清华 Conda 镜像拉取失败，尝试官方默认通道..." -ForegroundColor Yellow
        conda create -n grna-demo python=3.10 -y
    }
}

Write-Host "正在通过清华 PyPI 镜像安装 Web 界面依赖 (streamlit, pandas, openpyxl)..." -ForegroundColor Cyan
conda run -n grna-demo pip install streamlit pandas openpyxl -i $PIP_INDEX --trusted-host pypi.tuna.tsinghua.edu.cn

# 3. 检查并创建 crispr 环境（实时打分引擎）
Write-Host ""
Write-Host "[3/4] 配置实时打分引擎环境 (crispr)..." -ForegroundColor Yellow
if ($envsList -match "crispr\s") {
    Write-Host "crispr 环境已存在，跳过创建，直接校验/安装依赖..." -ForegroundColor Green
} else {
    Write-Host "正在创建 crispr 环境 (Python 3.10)..." -ForegroundColor Cyan
    conda create -n crispr python=3.10 -y -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ --override-channels
    if ($LASTEXITCODE -ne 0) {
        Write-Host "清华 Conda 镜像拉取失败，尝试官方默认通道..." -ForegroundColor Yellow
        conda create -n crispr python=3.10 -y
    }
}

Write-Host "正在通过清华 PyPI 镜像安装打分模型依赖 (genet, biopython, scikit-learn, joblib, scipy)..." -ForegroundColor Cyan
conda run -n crispr pip install pandas biopython scikit-learn joblib scipy genet==0.17.2 -i $PIP_INDEX --trusted-host pypi.tuna.tsinghua.edu.cn

# 部署预置的 DeepSpCas9 模型权重（避免从 GitHub 下载失败）
Write-Host "正在部署 DeepSpCas9 离线模型权重..." -ForegroundColor Cyan
$sitePackagesCode = "import inspect, genet.models; print(inspect.getfile(genet.models).replace('__init__.py', ''))"
$genetModelsDir = (conda run -n crispr python -c $sitePackagesCode).Trim()
$targetModelDir = Join-Path $genetModelsDir "DeepSpCas9"

if (-not (Test-Path $targetModelDir)) {
    New-Item -ItemType Directory -Force -Path $targetModelDir | Out-Null
}

$localModelSource = Join-Path $scriptDir "models\DeepSpCas9"
if (Test-Path $localModelSource) {
    Copy-Item -Path "$localModelSource\*" -Destination $targetModelDir -Force
    Write-Host "已成功拷贝离线模型权重到: $targetModelDir" -ForegroundColor Green
} else {
    Write-Host "未找到本地 models/DeepSpCas9 目录，genet 将在首次运行时尝试下载。" -ForegroundColor Yellow
}

# 验证打分引擎
Write-Host "正在验证打分引擎..." -ForegroundColor Cyan
$testResult = conda run -n crispr python scripts/predict.py
Write-Host "引擎自检输出:" -ForegroundColor Gray
Write-Host $testResult

# 4. 生成一键启动脚本 run_demo.bat
Write-Host ""
Write-Host "[4/4] 生成一键启动入口 run_demo.bat..." -ForegroundColor Yellow
$runBatPath = Join-Path $scriptDir "run_demo.bat"
$batContent = @"
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
    "D:\Miniconda\envs\crispr\python.exe"
    "D:\miniconda3\envs\crispr\python.exe"
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
    echo 尝试直接通过 conda run 启动...
    conda run -n grna-demo streamlit run app/app.py
) else (
    streamlit run app/app.py
)
pause
"@

[System.IO.File]::WriteAllText($runBatPath, $batContent, [System.Text.Encoding]::UTF8)

# 同时在上一级根目录创建快捷启动入口
$rootBatPath = Join-Path $scriptDir "..\一键启动Demo.bat"
$rootBatContent = @"
@echo off
chcp 65001 >nul
call "%~dp0cs_pipeline\run_demo.bat"
"@
[System.IO.File]::WriteAllText($rootBatPath, $rootBatContent, [System.Text.Encoding]::UTF8)

Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  恭喜！Web 演示工具已全部部署完成！" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "启动方式（任选一种）：" -ForegroundColor White
Write-Host "  1. 直接双击项目根目录下的: 一键启动Demo.bat" -ForegroundColor Cyan
Write-Host "  2. 直接双击: cs_pipeline\run_demo.bat" -ForegroundColor Cyan
Write-Host "  3. 在终端运行: conda run -n grna-demo streamlit run cs_pipeline/app/app.py" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键完成部署..."
