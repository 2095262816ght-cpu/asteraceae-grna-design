# 菊科菊苣族 CRISPR/Cas9 gRNA 设计工具（CS 管线）

一句话简介：以 DeepSpCas9 + CRISPRon 双模型打分经分层选择性 Beta-Binomial GLMM 排序集成（形态二模型，基于自有植物 Hi-TOM noB879 纯A级金标准训练）预测 gRNA 效率，扫描莴苣 T2T 完整基因组产生候选，结合多组织转录表达看板与 Cas-OFFinder 脱靶过滤，最终经 React + FastAPI 全栈系统交付「按基因检索 / 按序列打分」两种交互用法。

## 项目概述

**为什么做**：CRISPR 育种的第一步是选高效 gRNA，但现有效率预测工具全部用哺乳动物（人/鼠）数据训练，植物——尤其菊科——没有专用工具，"人源模型迁移到植物可不可靠"此前也没有定量答案。

**做了什么**（对应交付物）：

1. **数据**：系统核查并更正橡胶草（TKS）Hi-TOM 实测数据（扩表至 1,368 行 / 24 批次），经独立双重审计落地裁决并剔除 90 行未确认 B 级数据，构建出 879 行 / 16 基因组的 **`noB879` 纯 A 级金标准数据集**，修复 PAM 错记、坐标偏移、链向整列反转、indel 口径低估等 7 类历史问题（`docs/data-governance/problem.md`、`docs/reports/project_progress_report.md`）。经公开渠道穷尽检索确认：**这是该物种首个成规模的 per-guide 实测效率金标准数据集**；
2. **模型（v2.1 终版生产模型）**：双模型打分 + 8 维生物物理特征，采用**形态二（分层选择性 Beta-Binomial GLMM）**架构（`results/model_card_hier_bb_nob879_0921.md`）。通过选择性经验贝叶斯（Selective EB）批次效应收缩机制剥离批次随机扰动，推断纯序列生物学活性；独立测试集实现显著正相关 **$\rho = \mathbf{+0.342}$（$p = 7.89 \times 10^{-7}$，AUC = 0.7857）**，低混杂核心折突破至 **$\rho = \mathbf{+0.464}$**；
3. **科学结论**：定量回答"人源模型迁移植物是否可行"——三体系对照显示预训练模型在植物体系直接迁移存在严重失效（单模型 AUC 仅约 0.52，与随机无异），人源/植物公开数据简单混合训练无法带来增量；而结合分层贝叶斯建模与真实数据校正能显著提升序列活性判别能力（`results/model_comparison_nob879_report_0924.md`）；
4. **多组学时空决策**：整合莴苣 5 组织（根、茎、叶、花、种子）均值表达与 16 批生物学重复（方案 1/3/5），提供组织特异性敲除表型适宜性诊断与面板内功能性脱靶危害评估；结合橡胶草 S1–S9 发育时相数据（方案 6），量化产胶通路推荐转化窗口；
5. **工具（排序推荐定位）**：莴苣 T2T 基因组基因区扫描（1,387 万候选）→ Cas-OFFinder 脱靶过滤（错配≤3）→ Web 系统（React + FastAPI 全栈，见根目录 `backend/`、`frontend/`）：按基因输出**排序推荐表**（融合效率分、组织优先指数、功能性脱靶危害与着丝粒标注；用于同一基因内取 top 3–5 送实验终筛），或按 30nt 序列实时打分（WSL CRISPRon 真实调用与降级溯源）。

**当前版本**：`v2.1`（2026-09-25 冻结）；指标与变更的权威记录见 `results/CHANGELOG_0927.md` 与 `results/model_comparison_nob879_0921.csv`。

## 目录结构

```
cs_pipeline/
├── env/
│   ├── environment.yml          # 主管线 conda 环境（crispr：py3.10 + R4.3 + genet）
│   ├── environment_export_0909.yml  # crispr 环境完整导出（精确复现备查）
│   └── *.R / *.sh               # 备用安装与环境组装脚本（见「环境搭建」）
├── data/
│   ├── hitom/                   # Hi-TOM 处理主线（00–03 脚本引用）
│   │   ├── hitom_clean_v1.csv   # Hi-TOM 实测数据统一表（唯一权威输入）
│   │   ├── hitom_seq30_0909.csv # 补齐 30bp 上下文后的主表
│   │   └── crispron_io/         # CRISPRon 打分 IO（不入 git）
│   ├── demo/                    # demo 源数据（09 / prepare_demo_data.py 引用）
│   │   ├── demo_nlr50_candidates.csv  # demo 范围候选（49 个 NLR 基因，19,839 条）
│   │   └── demo_nlr50_genes.txt
│   ├── lettuce/                 # Cas-OFFinder 输入（casoffinder_input.txt 等，不入 git）
│   ├── raw/                     # 团队原始交付：hitom/（R0/R1 测序归档与汇总表）、
│   │                            #   screening_tools/、consolidation_sources/（不入 git）
│   └── reference_genomes/       # 三套参考基因组与注释：茎用生菜 v1.1c / 橡胶草 TKS /
│                                #   莴苣 T2T（不入 git；01/07 脚本从此处读取）
├── scripts/                     # 流水线脚本，按编号顺序执行（见「复现流程」）
├── results/                     # 产出表、图、冻结文档（CHANGELOG_0927.md 为指标冻结记录）
├── app/
│   ├── inference_client.py      # 跨环境模型推理客户端接缝（子进程调用打分引擎）
│   ├── batch_importer.py        # 批量表格导入 IO 适配器
│   ├── batch_session.py         # 批量打分生命周期深度模块
│   ├── recommendation_engine.py # 候选推荐与多组学决策引擎
│   └── score_deepspcas9_cli.py  # 打分子进程入口（stdin 进、CSV 出）
├── demo/                        # demo 运行时数据（app_data.csv 等，由 prepare_demo_data.py 生成）
├── docs/                        # 项目资料库（索引见 docs/README.md）：plans/ 方案分工、
│                                #   reports/ 工作报告、data-governance/ 数据治理、
│                                #   knowledge/ 笔记、paper/ 文献、survey/ 调研、
│                                #   notification/ 赛事通知、ppt/ 汇报PPT、patent/ 专利、_archive/ 存档
├── tools/                       # 外部工具（二进制与克隆不入 git，见「外部工具」）
├── README.md
└── requirements.txt
```

## 环境搭建（逐条命令，Windows + Anaconda Prompt / Git Bash）

> 评委快速验证与功能覆盖矩阵见根 [`README.md`](../README.md)「评审快速验证 / 完整功能安装」。
> 以下 conda 路线与 pip 路线**等价，二选一即可**。

```bash
# 方式 A（推荐）：pip，一条命令装齐
cd /d <本仓库所在目录>/cs_pipeline
pip install -r requirements.txt    # 主管线 + Web 后端 + DeepSpCas9（genet/TF2.9.3/torch/RNAfold）

# 方式 B（等价）：conda
conda env create -f env/environment.yml   # 环境名 crispr，py3.10 + R4.3 + genet 0.17.2
conda activate crispr

# CRISPRon 真实打分环境（可选；TF2.14 与上面的 TF2.9.3 无法同环境，故独立）
wsl -d Ubuntu-22.04 -- bash env/setup_crispron_wsl.sh
```

- `requirements.txt` 为**一文件装齐**（内部 `-r requirements-score.txt`）；`requirements-crispron.txt` 为 CRISPRon 独立环境。
- 未装 CRISPRon 环境时，`crispron` 特征降级为经验近似式并逐条标注 `approximated`，**其余全部功能不受影响**。
- R 侧备用：`BiocManager::install("crisprScore")`（R≥4.3，安装脚本 `env/install_crisprscore.R`）。注：本项目实际打分链路为 genet（DeepSpCas9，Windows 原生）+ CRISPRon 官方仓库（WSL），crisprScore 仅备用——其 DeepSpCas9 依赖 py2.7+TF1.4.1 无 Windows 包，且任何版本均不含 CRISPRon。

## 复现流程

### 1. 现行生产模型与多组学决策全流程（v2.1 权威路径）

```bash
conda activate crispr

# A. 生产模型训练（noB879 纯A级金标准 879 行，形态二分层 Beta-Binomial GLMM）
python scripts/15_train_hierarchical_bb_nob879.py  # 产出 meta_model_hier_bb_nob879_0921.joblib
python scripts/24_model_comparison_nob879.py       # 产出同口径三方横向对比总表与报告
python scripts/25_sensitivity_dual_grna_0924.py    # 产出双 gRNA 敏感性验证表

# B. 候选扫描与脱靶评估（莴苣 T2T 全外显子与启动子）
python scripts/07_scan_lettuce.py                  # 产生候选表 + scan_stats_0923.md
bash   scripts/08_casoffinder_run.sh               # Cas-OFFinder 脱靶（CPU / GPU分批脚本见 run_mini_batches.ps1）
python scripts/09_aggregate_offtarget.py           # 汇总脱靶计数 → results/offtarget_counts_0924.csv

# C. 多组学转录表达与发育时相决策（方案 1/3/5/6）
python scripts/16_prep_expression_features.py             # 表达特征矩阵与 LSA↔T2T crosswalk
python scripts/21_build_tissue_priority_recommendations.py # 方案3 组织优先指数表
python scripts/22_calc_tissue_offtarget_hazard.py          # 方案5 功能性脱靶危害表
python scripts/23_tks_developmental_window.py              # 方案6 橡胶草产胶发育时相曲线与推荐窗口

# D. 启动 Web 系统（React + FastAPI 全栈）
python demo/prepare_demo_data.py                   # 合并 demo 数据 → demo/app_data.csv（灌库输入）
cd .. && powershell -NoProfile -File run_fullstack.ps1   # 或双击根目录 一键启动全栈系统.bat
```

- 模型训练完成后，由 `scripts/predict.py` 的 `predict_efficiency(seq30_list)` 接口统一向 Web 系统供分（支持 WSL 原生 CRISPRon 真实调用及降级来源回溯）。
- **一键生成最终结果文件**：`python scripts/emit_results.py` → `results/results.csv`（字段规范见 [`results/RESULTS_SCHEMA.md`](results/RESULTS_SCHEMA.md)）。对**新序列**打分则用 `python scripts/predict.py` 或调用 `predict_efficiency()`。
- **关于 Jupyter Notebook**：《附件5》第二节第（4）项规定「如主运行入口已经能够完整复现流程，Notebook 不作为所有项目的强制文件」。本项目上述 A/B/C 三段脚本已可端到端完整复现（训练 → 扫描 → 脱靶 → 多组学决策 → 结果文件），故不额外提供 Notebook，以脚本链路为准。
- **训练 / 验证日志与随机种子**：见 [`logs/README.md`](logs/README.md)（`random_state=42` 全队统一，16 折 LOGO-CV 折级明细与运行耗时已归档）。

### 2. 历史阶段复现路径备查（v1.x / v2.0）
- `scripts/01–06`：v1.x 早期 487 行岭回归 Stacking 原型链路；
- `scripts/10–13`：v2.0 阶段重训链路（以改正版 xlsx 为源）；
- `scripts/14_public_mix_train.py`：公开人源/植物数据混合迁移实验（已证实无增量）。

## 模型与指标摘要

- **现行生产模型为形态二分层模型（`results/meta_model_hier_bb_nob879_0921.joblib`）**：
  - **数据集**：`noB879` 纯 A 级金标准（879 行 / 16 基因组 / 35 条 distinct guide）；
  - **模型架构**：分层选择性 Beta-Binomial GLMM（似然层建模 read count 二项抽样与过度离散，先验层通过选择性经验贝叶斯收缩批次效应随机截距）；
  - **权威文档**：`results/model_card_hier_bb_nob879_0921.md`（模型卡与局限性分析）、`results/model_comparison_nob879_0921.csv`（同口径对比表）、`results/model_comparison_nob879_report_0924.md`（可比性分析）；
  - **指标实测**：独立测试集（20% 留出）$\rho = \mathbf{+0.3424}$（$p = 7.89 \times 10^{-7}$，AUC = 0.7857）；低混杂多批次核心折（Class A）突破至中位数 $\rho = \mathbf{+0.4636}$；
  - **单模型对比**：在同口径植物实测集上，DeepSpCas9 与 CRISPRon 单用时 AUC 仅为 0.5242 / 0.5246（与随机无异），证明人源模型直接迁移植物失效，必须结合分层贝叶斯校正。
- 当前可复现的实测锚点：
  - DeepSpCas9 链路：示例序列 `ATCGGCTAAGCTAGGCTAGCATCGTGGATC` 打分 71.2494（Web 系统「按序列打分」可直接复现）；
  - 基因组扫描：45,770 基因、13,867,270 条候选、320 秒（`results/scan_stats_0923.md`）；
  - 脱靶：demo 范围 19,839 条 guide、6,088,827 个命中位点、mis3 脱靶中位数 16（`results/offtarget_runlog_0924.md`）；
  - 推理接口：`python scripts/predict.py` 经 WSL 原生调用 CRISPRon 得到真实打分 59.61，集成预测分 22.04。

## 外部工具

- **Cas-OFFinder v2.4.1**（2021-01-23 构建），Windows 64 位二进制；下载地址：https://github.com/snugel/cas-offinder （Releases 页 win64 包，解压得 `cas-offinder.exe` 置于 `tools/cas-offinder/`，不随代码包发布）。
- **CRISPRon / CRISPRoff**（RTH-tools，GPL/AGPL）：仓库克隆与模型文件不入 git，由 `env/setup_crispron_wsl.sh` 在 WSL 中重建（https://github.com/RTH-tools/crispron）。
- **genet 0.17.2**（pip）：DeepSpCas9 TF2 封装，随 `env/environment.yml` 安装；首次 predict 自动下载模型 checkpoint（约 700 KB，需联网）。

## 数据说明

完整的数据来源、版本、获取时间、用途、许可、清洗记录、训练/验证/测试划分与去重与数据泄漏防控措施见 [`data/README.md`](data/README.md)（《附件5》第三节溯源要求）。

| 数据 | 是否随包发布 | 原因 | 获取方式 |
|---|---|---|---|
| `data/reference_genomes/`（茎用生菜 v1.1c ~2.5 Gb、橡胶草 TKS ~1.2 Gb、莴苣 T2T ~2.5 Gb 及各自注释） | ✅ 随包发布 | — | 生菜两套由团队网盘提供；莴苣 T2T 在其论文 Figshare 页面下载 fasta/GFF3；`2-1_TKS.genome.fasta`/`3-1_LsT2T.*` 为 01/07 脚本的直接输入 |
| `data/lettuce/`（Cas-OFFinder 输入 + 着丝粒 bed） | ✅ 随包发布 | 可再生 | `casoffinder_input.txt` 由 B2 候选生成（随 git 发布于 `data/lettuce/`）；着丝粒坐标出自莴苣 T2T 论文补充表 |
| `data/raw/`（Hi-TOM 原始测序交付 R0/R1 归档、PCR 检测图、合并源表、筛查序列） | ❌ 不随包发布 | **团队自有未发表实验数据**、体积大 | 团队共享网盘为权威源；`data/hitom/hitom_clean_v1.csv` 为清洗后快照，随代码发布 |
| `results/offtarget_raw_0924.txt`（399 MB 原始脱靶输出） | ❌ 不随包发布 | 体积过大、可再生 | 由 `scripts/run_mini_batches.ps1` + `scripts/09_aggregate_offtarget.py` 复现；汇总表 `offtarget_counts_0924.csv` 随代码发布 |
| CRISPRon 模型权重、genet checkpoint | ❌ 不随包发布 | 第三方模型文件 | 由上述安装步骤自动获取 |

## 匿名化说明

本仓库为匿名评审交付版本：全部 git 提交者为 `team <team@example.com>`；交付快照不含 `.git` 目录；源码、文档、配置中不含任何校名、院系名、师生姓名与个人路径（10.3 专项检查清单见团队工作报告）。
