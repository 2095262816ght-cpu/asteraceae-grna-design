# 菊科菊苣族 CRISPR/Cas9 gRNA 设计与脱靶评估系统

> 交付基准版本：`v2.1`（2026-09-25 冻结）

---

## 💡 项目概述与核心亮点

本项目针对植物育种领域（特别是菊科菊苣族：橡胶草、莴苣等）缺乏高质量 gRNA 效率预测工具、人源预训练模型直接迁移存在系统偏差的痛点，构建了面向全基因组扫描、高精度打分、脱靶过滤与多组学时空表达决策的一体化流水线。

1. **首个成规模植物实测金标准数据集（`noB879`）**：
   - 深入审计并治理橡胶草（TKS）Hi-TOM 测序数据（1,368 行 / 24 批次），系统修复 PAM 错记、坐标偏移、链向整列反转、indel 口径低估等 7 类历史问题，剔除多候选竞争未确认样本，构建出 879 行 / 16 基因组的纯 A 级金标准数据集。
   - 根目录下保留的 `_check_*.py`、`_fix_*.py` 等 39 个 `_*.py` 审计脚本为数据治理期间的微观读段与坐标对齐可复现审计记录。
2. **算法突破：分层选择性 Beta-Binomial GLMM（形态二模型）**：
   - 融合预训练双模型（DeepSpCas9 + CRISPRon）打分与 8 维生物物理特征（合计 10 维标准特征）；
   - 建立选择性经验贝叶斯（Selective EB）批次效应随机截距收缩机制，剥离实验批次扰动，推断纯序列生物学活性；
   - 独立测试集实现正向相关 $\rho = \mathbf{+0.342}$（$p = 7.89 \times 10^{-7}$），低混杂核心折突破至 $\rho = \mathbf{+0.464}$。
3. **全基因组候选扫描与 Cas-OFFinder 脱靶过滤**：
   - 完成莴苣 T2T 完整基因组 45,770 个基因的全外显子与启动子区扫描（全基因目录共 45,981 个基因，其余为无有效候选的基因），产出 1,386.7 万条候选位点；
   - 借助 Cas-OFFinder（GPU/CPU）完成脱靶位点检索与着丝粒抑制区过滤。
4. **多组学时空表达看板与转化窗口决策**：
   - 整合莴苣 5 组织（根、茎、叶、花、种子）均值表达与 16 批生物学重复，提供组织特异性敲除适宜性诊断；
   - 整合橡胶草 S1–S9 发育时相多组织表达谱，量化产胶关键通路（CPT、REF、SRPP）的推荐转化窗口。
5. **交互式 Web 系统（React 19 + FastAPI 全栈）**：
   - 交付开箱即用的 Web 系统：全基因组靶基因输入端（莴苣 45,981 个 `LsT2T1G*`–`LsT2T9G*` 基因 + 49 个 NLR 代表基因 `LsaT2T01G*` 双注释命名空间，即输即搜），支持候选推荐表过滤下载与自定义 30bp 序列实时打分（WSL CRISPRon 真实调用与降级溯源）。

---

## 🖥️ 运行环境要求

| 项目 | 要求 |
|---|---|
| **Python 解释器** | Python 3.10（实测 3.10.21；`cs_pipeline/env/environment.yml` 与 `backend/Dockerfile`（`python:3.10-slim`）同口径） |
| **操作系统** | Windows 10/11 x64（一键脚本，Anaconda Prompt / Git Bash）或 Linux 容器（`docker-compose.yml`，Windows 下需 Docker Desktop）；CRISPRon 真实打分走 WSL2 Ubuntu-22.04（`cs_pipeline/env/setup_crispron_wsl.sh`）或容器内置 venv-crispron |
| **CUDA / 驱动** | 训练与打分均为 CPU（`cs_pipeline/requirements-score.txt` 锁 `torch==2.14.0+cpu`、`tensorflow==2.9.3`，无 CUDA 依赖），无需 NVIDIA 驱动；仅 Cas-OFFinder 脱靶检索可选 GPU 加速（需 NVIDIA 驱动与 CUDA Toolkit），CPU 分批亦可运行 |
| **系统库** | ViennaRNA 2.6.4（`RNAfold`，CRISPRon 依赖，经 conda/bioconda 或容器 micromamba 安装）；R ≥ 4.3 仅备用（`crisprScore`，`cs_pipeline/env/install_crisprscore.R`）；samtools 可选（无 Windows 构建，`.fai` 索引以 pyfaidx 替代） |
| **硬件** | 64 位多核 CPU；内存建议 ≥ 16 GB（全基因组扫描与灌库）；磁盘建议 ≥ 20 GB 空闲（参考基因组约 6.3 GB + 候选库 `lifescience.db` 约 2 GB，Docker 镜像与离线包另计）；GPU 非必需 |

**依赖清单（版本均已列明或锁定）**：`cs_pipeline/requirements.txt`（主管线直接依赖，锁实测版本）、`cs_pipeline/env/environment.yml` + `cs_pipeline/env/environment_export_0909.yml`（Conda 环境定义与全量传递依赖锁定）、`cs_pipeline/requirements-score.txt` / `cs_pipeline/requirements-crispron.txt`（打分子环境，精确锁定）、`backend/requirements.txt`、`frontend/package-lock.json`。

---

## 🚀 评审快速验证（3 条命令）

> 《附件5》第七节：评测平台将依据 **README 与 requirements.txt** 配置环境并运行 `predict.py` 等脚本，
> 核对运行结果与提交清单的一致性。以下三步即可完成该核对。

```bash
cd cs_pipeline
pip install -r requirements.txt        # 一条命令装齐：主管线 + Web 后端 + DeepSpCas9 打分
python scripts/emit_results.py         # 生成 results/results.csv，与提交件逐字节一致
```

预期末行输出：`完成 -> .../results/results.csv  (1365.4 MiB)`。
生成的 `results.csv` 与随包提交的 `cs_pipeline/results/results.csv` **应完全一致**（字段规范与校验说明见 [`cs_pipeline/results/RESULTS_SCHEMA.md`](cs_pipeline/results/RESULTS_SCHEMA.md)）。

推理打分（含 DeepSpCas9 真实模型）：

```bash
python scripts/predict.py
# 预期输出: Example predictions: [22.04, ...]   —— 锚点序列 ATCGGCTAAGCTAGGCTAGCATCGTGGATC 集成分 22.04
```

---

## 🛠️ 完整功能安装

只需 **Python 3.10**。下表列出每个功能需要什么、装完能干什么：

| 功能 | 需要什么 | 状态 |
|---|---|---|
| 结果文件生成与复核（`emit_results.py`） | `pip install -r cs_pipeline/requirements.txt` | ✅ 上一节已覆盖 |
| **模型推理 / DeepSpCas9 打分**（`predict.py`） | 同上 | ✅ 已覆盖 |
| **生产模型训练**（`15_train_*.py`）、扫描、脱靶、多组学 | 同上 | ✅ 已覆盖 |
| **Web 后端**（FastAPI）+ 测试套件（`pytest tests/`） | 同上 | ✅ 已覆盖 |
| **Web 前端**（React 19 界面） | 另需 Node.js ≥ 20 + `npm install` | 见步骤 3 |
| **CRISPRon 真实打分**（不装则降级为近似式并标注） | 另需 WSL2 + 第二个 Python 环境 | 见步骤 4 |

### 1. Python 环境（装完即可跑模型、训练、后端、测试）

```bash
cd cs_pipeline
pip install -r requirements.txt
```

> **为什么 CRISPRon 不在这个文件里？**
> `genet==0.17.2` 元数据锁死 `tensorflow<2.10`（本环境装 2.9.3），而 CRISPRon 需要 `tensorflow==2.14.0`。
> 两个 TF 版本**无法共存于同一 pip 环境**（上游包硬约束），故 CRISPRon 独立成第二环境。
> 未装第二环境时，`crispron` 特征自动降级为经验近似式 `deepspcas9×0.95+(Tm−50)×0.25` 并**逐条标注 `approximated`**，
> 界面会明确提示偏差约 15%，**其余全部功能不受影响**。

### 2. DeepSpCas9 离线权重固化（可选，避免运行时联网下载）

`predict.py` 首次运行会自动下载模型 checkpoint（约 700 KB）。离线或网络受限时，用随包权重预先固化：

```bash
cd cs_pipeline
python -c "import inspect,os,shutil,genet.models;src='models/DeepSpCas9';dst=os.path.join(os.path.dirname(inspect.getfile(genet.models)),'DeepSpCas9');os.makedirs(dst,exist_ok=True);[shutil.copy(f,dst) for f in os.listdir(src)];print('已固化到',dst)"
```

> 权重文件 `cs_pipeline/models/DeepSpCas9/PreTrain-Final-*` 已随包提供，无需下载。

### 3. Web 前端（React 19 + Vite）

```bash
# 需 Node.js ≥ 20
cd frontend
npm install
```

启动全栈（自动建库灌库 + FastAPI :8000 + Vite :5173 + 自动开浏览器）：

```bash
# Windows：双击根目录 一键启动全栈系统.bat
# 或命令行：
powershell -NoProfile -File run_fullstack.ps1
```

- 前端界面：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

> 首次启动会灌库（45,981 基因 + 452 万候选），约数分钟；已存在 `lifescience.db` 时秒级跳过。
> 数据库用 SQLite（`lifescience.db`，已随包），**无需安装 PostgreSQL**；PostgreSQL 仅在 `docker-compose.yml` 路线使用。

### 4. CRISPRon 真实打分（可选但推荐）

需要 **WSL2 Ubuntu-22.04** + 该发行版内的 `crispron` 环境：

```bash
cd cs_pipeline
wsl -d Ubuntu-22.04 -- bash env/setup_crispron_wsl.sh
```

装完后 `predict.py` 会自动走 WSL 原生实跑，`crispron_source` 由 `approximated` 变为 `wsl_real`。

- **锚点自检**：`ATCGGCTAAGCTAGGCTAGCATCGTGGATC` 应返回 `CRISPRon=59.61`、`crispron_source=wsl_real`、集成分 `22.04`。
- **版本说明**：pip 路线（步骤 1）经 genet 带入的是 ViennaRNA 2.7.2；WSL CRISPRon 环境实测用 ViennaRNA 2.6.4（见 `requirements-crispron.txt`）。两者不互相影响。

### 5. Docker 容器路线（可选）

`docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile` 已提供，容器内 `CRISPRON_MODE=native` 走原生 CRISPRon（构建期自带 `wsl_real`/`59.61` 断言）：

```bash
docker compose up --build
```

> Windows 需 Docker Desktop。首次构建镜像并灌库约 10–30 分钟。

---

## 📂 项目结构总览

算法管线代码、数据、模型与文档集中于 [`cs_pipeline/`](cs_pipeline/README.md)，全栈系统位于 `backend/`（FastAPI）与 `frontend/`（React 19）：

```text
project\
├── 一键启动全栈系统.bat         # 全栈启动入口（FastAPI + React，自动灌库）
├── run_fullstack.ps1            # 全栈本地启动实现（建库灌库 + uvicorn + Vite）
├── docker-compose.yml           # Docker 全栈编排（数据库、后端、前端；可选路线）
├── _check_*.py / _fix_*.py 等  # Hi-TOM 原始测序数据 7 类问题核对与审计脚本（39 个）
├── README.md                    # 本文件（项目导航总门户）
├── backend/                    # FastAPI 后端（API、服务层、数据库灌库与自动化测试）
├── frontend/                   # React 19 + TypeScript + Vite + Tailwind CSS 前端
└── cs_pipeline/                # 主流水线工程目录
    ├── app/                    # 打分子进程与深度模块
    │   ├── inference_client.py # 跨环境模型推理客户端接缝
    │   ├── batch_importer.py   # 批量表格导入 IO 适配器
    │   ├── batch_session.py    # 批量打分生命周期深度模块
    │   ├── recommendation_engine.py # 候选推荐与多组学决策引擎
    │   └── score_deepspcas9_cli.py # 子进程打分通信接口
    ├── core/                   # 领域核心（序列规范、排名语义、ATAC 注释）
    ├── scripts/                # 完整流程执行脚本（编号 00–29，19/20 缺号）
    │   ├── 15_train_hierarchical_bb_nob879.py # 生产模型训练主脚本
    │   ├── 24_model_comparison_nob879.py      # 同口径模型横向对比总表
    │   ├── predict.py          # 官方统一推理预测接口
    │   ├── emit_results.py     # 一键生成附件5 标准化最终结果文件 results.csv
    │   ├── features_common.py  # 10 维标准特征单一来源模块
    │   ├── hier_bb_model.py    # 分层选择性 Beta-Binomial 模型
    │   └── crispron_wsl.py     # WSL 内原生 CRISPRon 真实调用
    ├── data/                   # 经清洗整理的结构化数据集与表达矩阵
    │   ├── hitom/              # Hi-TOM 测序数据与序列主表
    │   ├── expression/         # 莴苣 5 组织与橡胶草时相多组学表达矩阵
    │   ├── lettuce/            # Cas-OFFinder 脱靶检索输入与批次文件
    │   ├── reference_genomes/  # 参考基因组 FASTA/GFF 与 NLR、通路注释
    │   └── demo/               # Web 演示所需代表候选与基因集
    ├── demo/                   # Web 演示数据准备与重打分脚本
    ├── models/                 # 预训练模型权重与离线包
    ├── results/                # 产出评估报告、模型卡与对比表
    │   ├── model_card_hier_bb_nob879_0921.md # 官方生产模型卡（含局限性与 SNP 噪声分析）
    │   ├── model_comparison_nob879_0921.csv  # 官方同口径横向对比总表
    │   ├── CHANGELOG_0927.md   # 指标冻结与变更权威记录
    │   └── offtarget_runlog_0924.md # 脱靶运行审计日志
    ├── requirements.txt        # 主环境依赖（另有 requirements-score.txt / requirements-crispron.txt 子环境清单）
    ├── tools/                  # 第三方工具集成（CRISPRon、NLR 注释、Windows shim）
    ├── env/                    # 环境定义配置（Conda YAML 与初始化脚本）
    ├── docs/                   # 详尽资料库（方案分工、工作报告、文献笔记）
    └── tests/                  # 自动化无头测试套件
```

---

## 📑 关键文档导航

- [流水线技术与复现手册](cs_pipeline/README.md)：环境搭建、依赖安装、从原始测序到 Web 系统的全流程复现步骤；
- [项目资料库索引](cs_pipeline/docs/README.md)：分工详案、工作报告、理论笔记、文献调研与赛事材料总目录；
- [项目全景审计进展报告](cs_pipeline/docs/reports/project_progress_report.md)：数据治理闭环、模型突破历程、工程阻断闭环与多组学实施方案；
- [生产模型卡（v2.1）](cs_pipeline/results/model_card_hier_bb_nob879_0921.md)：数据来源、特征定义、评估指标、双 guide 错配说明与已知标签口径局限分析。

---

## 🔒 匿名合规声明

本仓库遵循匿名交付与隐私规范：
1. 代码、文档、配置及注释中不包含任何高校名称、院系名称与个人真实姓名；
2. 彻底剔除所有本地开发机绝对路径与个人用户名；
3. 外部引用工具及公开镜像源（如清华开源软件镜像站）均为公共技术基础设施，不代表任何所属单位。

---

## 📦 大文件获取

> git 仅收录代码与 Markdown 文档；PDF / docx / xlsx 等大文件被 .gitignore 忽略，团队网盘为权威源。
> 如需获取数据请访问网盘：https://pan.quark.cn/s/ca03e23f73f6
> 联系邮箱获取提取码：2095262816ght@gmail.com
