[CmdletBinding()]
param(
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  菊科 CRISPR/Cas9 基因编辑全栈系统 - 制作离线交付镜像包" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
if (-not $ProjectRoot) {
    $ProjectRoot = "d:\lifesciencechallenge"
}
Set-Location $ProjectRoot

# 0. 自动补全 Docker 路径 (确保刚安装无需重启也能直接识别)
$DockerCandidates = @(
    "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin",
    "C:\Program Files\Docker\Docker\resources\bin"
)
foreach ($dPath in $DockerCandidates) {
    if ((Test-Path $dPath) -and ($env:Path -notlike "*$dPath*")) {
        $env:Path = "$dPath;$env:Path"
    }
}

# 1. 检查 Docker 命令行是否可用
$DockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $DockerCmd) {
    Write-Host "[错误] 本机尚未安装或未将 Docker 配置到系统 PATH！" -ForegroundColor Red
    Write-Host "制作离线镜像包需要先安装并启动 Docker Desktop：" -ForegroundColor Yellow
    Write-Host "官网下载地址: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
    Write-Host ""
    Write-Host "安装完成后，请打开 Docker Desktop，等待右下角显示绿色 'Engine running'，然后再运行本脚本。" -ForegroundColor Yellow
    Write-Host ""
    if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
    exit 1
}

# 2. 检查 Docker Engine 是否已启动
Write-Host "[1/4] 检查 Docker 运行状态..." -ForegroundColor Yellow
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Engine 未启动"
    }
    Write-Host "      Docker Engine 运行正常。" -ForegroundColor Green
} catch {
    Write-Host "[错误] 检测到 Docker 命令行，但 Docker Desktop 服务尚未启动！" -ForegroundColor Red
    Write-Host "请在 Windows 桌面或开始菜单中打开 'Docker Desktop'，并等待其完全启动。" -ForegroundColor Yellow
    Write-Host ""
    if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }
    exit 1
}

$OfflineDir = Join-Path $ProjectRoot "deploy_offline"
if (-not (Test-Path $OfflineDir)) {
    New-Item -ItemType Directory -Path $OfflineDir -Force | Out-Null
}

# 3. 拉取基础镜像并编译前后端生产镜像
Write-Host "[2/4] 正在拉取基础镜像并编译生产容器..." -ForegroundColor Yellow
Write-Host "      正在拉取 postgres:16-alpine..." -ForegroundColor Gray
docker pull postgres:16-alpine
if ($LASTEXITCODE -ne 0) {
    Write-Error "拉取 postgres:16-alpine 失败，请检查网络。"
}

Write-Host "      正在编译 FastAPI 后端与 React 19 Nginx 前端镜像..." -ForegroundColor Gray
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker 镜像构建失败，请检查构建日志。"
}
Write-Host "      镜像构建成功！" -ForegroundColor Green

# 4. 导出镜像包
$TarPath = Join-Path $OfflineDir "crispr_images.tar"
Write-Host "[3/4] 正在导出镜像到: $TarPath (导出约需 2~5 分钟，镜像包约 7~8GB 含双 TF 打分栈)..." -ForegroundColor Yellow
docker save -o $TarPath crispr_backend:latest crispr_frontend:latest postgres:16-alpine
if ($LASTEXITCODE -ne 0) {
    Write-Error "镜像导出失败！"
}

# 5. 暂存外挂数据文件与启动脚本（镜像内不含大数据，见 .dockerignore 与 docker-compose.yml 挂载）
Write-Host "[4/4] 正在暂存外挂数据文件与启动脚本..." -ForegroundColor Yellow
Copy-Item (Join-Path $ProjectRoot "docker-compose.yml") $OfflineDir -Force
Copy-Item (Join-Path $ProjectRoot "import_offline_package.ps1") $OfflineDir -Force
Copy-Item (Join-Path $ProjectRoot "一键导入镜像并启动.bat") $OfflineDir -Force

$DataFiles = @(
    "cs_pipeline\data\reference_genomes\3-1_LsT2T.genome.fa",
    "cs_pipeline\data\reference_genomes\3-1_LsT2T.genome.fa.fai",
    "cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta",
    "cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta.fai",
    "cs_pipeline\results\lettuce_all_genes_top100_candidates.csv"
)
$MissingData = @()
foreach ($rel in $DataFiles) {
    $src = Join-Path $ProjectRoot $rel
    if (-not (Test-Path $src)) {
        $MissingData += $rel
        Write-Host "      [缺失] $rel（对应功能将降级）" -ForegroundColor Red
        continue
    }
    $dst = Join-Path $OfflineDir $rel
    New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
    Write-Host "      复制 $rel ..." -ForegroundColor Gray
    Copy-Item $src $dst -Force
}
if ($MissingData.Count -gt 0) {
    Write-Host "      警告: $($MissingData.Count) 个外挂数据文件缺失，交付包将不完整！" -ForegroundColor Yellow
} else {
    Write-Host "      外挂数据文件齐全，全功能可用。" -ForegroundColor Green
}

$TarSizeMB = [math]::Round((Get-Item $TarPath).Length / 1MB, 2)
$DataSizeMB = [math]::Round(((Get-ChildItem (Join-Path $OfflineDir "cs_pipeline") -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 2)
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  恭喜！离线交付包已制作成功！" -ForegroundColor Green
Write-Host "  镜像包大小: $TarSizeMB MB（大数据外挂不进镜像）" -ForegroundColor White
Write-Host "  外挂数据大小: $DataSizeMB MB（cs_pipeline/ 目录，compose 挂载）" -ForegroundColor White
Write-Host "  产物目录: $OfflineDir" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "【交付指南】" -ForegroundColor Yellow
Write-Host "直接将 deploy_offline 文件夹压缩为 ZIP 发送给对方即可（保持目录结构完整）。" -ForegroundColor White
Write-Host "对方解压后只需双击运行 '一键导入镜像并启动.bat'，断网也可快速拉起！" -ForegroundColor White
Write-Host "切勿只发 crispr_images.tar：外挂数据文件缺失会导致脱靶计数/TKS/全基因组灌库功能降级。" -ForegroundColor Yellow
Write-Host ""
if (-not $NonInteractive) { Read-Host "按 Enter 键退出" }