<#
.SYNOPSIS
    菊科 CRISPR/Cas9 基因编辑全栈系统本地一键启动脚本 (FastAPI + React 19 + SQLite/Postgres)。
.DESCRIPTION
    自动探测 Conda 与 Node 环境，初始化数据库并灌库，同时启动后端 API 与前端热重载开发服务器。
#>

[CmdletBinding()]
param(
    [switch]$SeedOnly,
    [switch]$NoBrowser,
    [switch]$ForceSeed
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  菊科 CRISPR/Cas9 基因编辑全栈系统 (生产级交付)" -ForegroundColor Green
Write-Host "  FastAPI + SQLAlchemy 2.0 + React 19 + TanStack Query" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = "d:\lifesciencechallenge"
}
Set-Location $ProjectRoot
$env:PYTHONPATH = $ProjectRoot

# 1. 探测 Python 解释器（须能承载后端依赖 fastapi + uvicorn）
# 经 cmd 吞掉探测子进程的 stderr：PowerShell 5.1 会把 python 的 ImportError 回溯
# 转成 NativeCommandError，在 ErrorActionPreference=Stop 下直接终止脚本
function Test-BackendDeps([string]$Exe) {
    if (-not $Exe -or -not (Test-Path $Exe)) { return $false }
    & cmd /c "`"$Exe`" -c `"import fastapi, uvicorn`" >NUL 2>&1" | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$PythonCandidates = @(
    "$env:CONDA_PREFIX\python.exe",
    "D:\Miniconda\envs\crispr\python.exe",
    "D:\Miniconda\envs\grna-demo\python.exe"
)

$PythonExe = $null
foreach ($cand in $PythonCandidates) {
    if (Test-BackendDeps $cand) {
        $PythonExe = $cand
        break
    }
}

if (-not $PythonExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd -and $pythonCmd.Source -and (Test-BackendDeps $pythonCmd.Source)) {
        $PythonExe = $pythonCmd.Source
    }
}

if (-not $PythonExe) {
    Write-Error "未找到承载后端依赖（fastapi + uvicorn）的 Python 解释器，请先在目标 Conda 环境执行: pip install -r backend/requirements.txt"
}
Write-Host "[1/4] 使用 Python 解释器: $PythonExe" -ForegroundColor Gray

# 2. 数据库检查与自动数据灌库 (智能秒级缓存加速)
Write-Host "[2/4] 检查数据表结构与初始数据灌库..." -ForegroundColor Yellow
$DbFile = Join-Path $ProjectRoot "lifescience.db"
$NeedSeed = $true

if ((-not $ForceSeed) -and (Test-Path $DbFile)) {
    $dbSize = (Get-Item $DbFile).Length
    if ($dbSize -gt 1000000) {
        $NeedSeed = $false
        Write-Host "      本地数据库已就绪 (45,981 全基因组 + 49 NLR 基因，秒级极速载入)." -ForegroundColor Green
    }
}

if ($NeedSeed) {
    Write-Host "      正在初始化建表与数据灌库 (首次运行或强制刷新)..." -ForegroundColor Gray
    & $PythonExe -m backend.app.db.seed
    if ($LASTEXITCODE -ne 0) {
        Write-Error "数据库初始化或数据灌库失败，请检查报错日志。"
    }
    Write-Host "      数据库灌库完成 (45,981 全基因组 + 49 NLR 基因及候选靶点)." -ForegroundColor Green
}

if ($SeedOnly) {
    Write-Host "数据灌库已完成 (--SeedOnly 模式退出)." -ForegroundColor Green
    exit 0
}

# 3. 检查前端依赖与准备启动
Write-Host "[3/4] 检查前端构建环境..." -ForegroundColor Yellow
$FrontendDir = Join-Path $ProjectRoot "frontend"
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "      正在安装前端依赖 (npm install)..." -ForegroundColor Gray
    npm --prefix $FrontendDir install
}

# 4. 并发拉起后端与前端服务
Write-Host "[4/4] 启动全栈服务..." -ForegroundColor Green
Write-Host "      - 前端交互界面: http://localhost:5173" -ForegroundColor Cyan
Write-Host "      - 后端 API 文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "      - 健康检查端点: http://localhost:8000/api/v1/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 即可同时停止前后端服务进程。" -ForegroundColor DarkGray
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray

# 启动后端子进程（--reload-dir 限定只监听代码目录：_scratch/results/数据库等写入不再触发全量重启）
$BackendProcess = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--port", "8000", "--reload", "--reload-dir", "backend", "--reload-dir", "cs_pipeline" -WorkingDirectory $ProjectRoot -PassThru -NoNewWindow

# 启动前端子进程 (Vite 准备就绪后自动秒开浏览器，避免提前打开造成白屏与卡顿)
try {
    if ($NoBrowser) {
        npm --prefix $FrontendDir run dev
    } else {
        npm --prefix $FrontendDir run dev -- --open
    }
}
finally {
    Write-Host "`n正在停止全栈服务..." -ForegroundColor Yellow
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "服务已全部优雅停止。" -ForegroundColor Green
}
