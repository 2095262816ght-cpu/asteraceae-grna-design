[CmdletBinding()]
param(
    [switch]$NonInteractive,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  菊科 CRISPR/Cas9 基因编辑全栈系统 - 离线导入并启动" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$Root = $PSScriptRoot
if (-not $Root) { $Root = (Get-Location).Path }
Set-Location $Root

# 0. 自动补全 Docker 路径
foreach ($dPath in @("$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin", "C:\Program Files\Docker\Docker\resources\bin")) {
    if ((Test-Path $dPath) -and ($env:Path -notlike "*$dPath*")) { $env:Path = "$dPath;$env:Path" }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] 未检测到 Docker！请先安装并启动 Docker Desktop：https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
    exit 1
}
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "engine down" }
} catch {
    Write-Host "[错误] Docker Desktop 尚未启动，请等待右下角显示 'Engine running' 后重试。" -ForegroundColor Red
    if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
    exit 1
}

# 1. 校验外挂数据文件（缺失不阻断启动，但如实告知哪些功能会降级）
Write-Host "[1/3] 校验外挂数据文件..." -ForegroundColor Yellow
$DataChecks = @(
    @{ Path = "cs_pipeline\data\reference_genomes\3-1_LsT2T.genome.fa";        Need = "脱靶计数、Tab 2 基因组回贴" },
    @{ Path = "cs_pipeline\data\reference_genomes\3-1_LsT2T.genome.fa.fai";    Need = "脱靶计数、Tab 2 基因组回贴" },
    @{ Path = "cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta";       Need = "橡胶草 (TKS) 预置参考包" },
    @{ Path = "cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta.fai";   Need = "橡胶草 (TKS) 预置参考包" },
    @{ Path = "cs_pipeline\results\lettuce_all_genes_top100_candidates.csv";   Need = "全基因组灌库（缺失时仅灌 49 NLR demo 数据）" }
)
$Missing = @()
foreach ($c in $DataChecks) {
    if (-not (Test-Path (Join-Path $Root $c.Path))) {
        $Missing += $c
        Write-Host "      [缺失] $($c.Path) —— 影响: $($c.Need)" -ForegroundColor Red
    }
}
if ($Missing.Count -eq 0) {
    Write-Host "      数据文件齐全，全功能可用。" -ForegroundColor Green
} else {
    Write-Host "      警告: $($Missing.Count) 个数据文件缺失，对应功能将降级（不影响其余功能）。" -ForegroundColor Yellow
}

# 2. 导入镜像（仅首次需要；镜像已存在则跳过，日常启动秒级）
$TarPath = Join-Path $Root "crispr_images.tar"
$Images = @("crispr_backend:latest", "crispr_frontend:latest", "postgres:16-alpine")
$NeedLoad = [bool]$Force
if (-not $NeedLoad) {
    foreach ($img in $Images) {
        docker image inspect $img 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $NeedLoad = $true; break }
    }
}
if ($NeedLoad) {
    if (-not (Test-Path $TarPath)) {
        Write-Host "[错误] 未找到 $TarPath 且本机镜像不全，请确认离线包完整。" -ForegroundColor Red
        if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
        exit 1
    }
    Write-Host "[2/3] 正在导入镜像（约 2~5 分钟）..." -ForegroundColor Yellow
    docker load -i $TarPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 镜像导入失败！" -ForegroundColor Red
        if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
        exit 1
    }
} else {
    Write-Host "[2/3] 镜像已存在，跳过导入（如需强制重新导入: 传入 -Force）..." -ForegroundColor Green
}

# 3. 启动全栈（镜像已导入，无需构建）
Write-Host "[3/3] 正在启动容器（首次启动灌库约 10~30 分钟，页面就绪以灌库完成为准）..." -ForegroundColor Yellow
docker compose up -d --no-build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 容器启动失败，请运行 docker compose logs backend 查看日志。" -ForegroundColor Red
    if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  启动成功！浏览器访问: http://localhost" -ForegroundColor Green
Write-Host "  停止系统: docker compose down" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
Start-Process "http://localhost"
if (-not $NonInteractive) { Read-Host "按 Enter 键关闭窗口" }
