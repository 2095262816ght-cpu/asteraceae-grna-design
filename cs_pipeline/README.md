# 菊科菊苣族 CRISPR/Cas9 gRNA 设计工具（CS 管线）

一句话简介：以 DeepSpCas9 + CRISPRon 双模型打分经岭回归 Stacking 集成（自有植物 Hi-TOM 数据训练/验证）预测 gRNA 效率，扫描莴苣 T2T 基因组基因区产生候选，Cas-OFFinder 脱靶过滤，最终经 Streamlit demo 交付「按基因检索 / 按序列打分」两种用法。

## 项目概述

**为什么做**：CRISPR 育种的第一步是选高效 gRNA，但现有效率预测工具全部用哺乳动物（人/鼠）数据训练，植物——尤其菊科——没有专用工具，"人源模型迁移到植物可不可靠"此前也没有定量答案。

**做了什么**（对应交付物）：

1. **数据**：系统核查并更正橡胶草（TKS）Hi-TOM 实测数据（491 行 / 23 条 guide / 14 基因），修复 PAM 错记、坐标偏移、链向整列错误、indel 口径低估等 7 类问题，每处更正均有基因组/原始 reads 证据（`docs/problem.md`、`docs/problem2.md`）。经公开渠道穷尽性检索确认：**这是该物种首个成规模的 per-guide 效率数据集**；
2. **模型**：双模型打分 + 序列特征岭回归 Stacking（`results/model_card_full_0916.md`）。LOGO-CV 中位 Spearman ρ=0.414，**未达 ρ≥0.5 达标线（如实）**，瓶颈为 distinct guide 数量（23 条）而非方法；
3. **科学结论**：定量回答"人源模型迁移植物是否可行"——三体系对照显示迁移可行性是**数据集特异的**（本氏烟 ρ≈0.85 良好 / 番茄原生质体 ρ≈0.03 失效 / 橡胶草部分有效），且人源/植物公开数据混合训练均不能带来增量（`results/transferability_0917.md`）；
4. **工具（排序推荐定位）**：莴苣 T2T 基因组基因区扫描（1,387 万候选）→ Cas-OFFinder 脱靶过滤（错配≤3）→ Streamlit demo：按基因输出**排序推荐表**（效率分+脱靶数+着丝粒标注；效率分用于同一基因内取 top 3–5 送实验终筛，非绝对效率承诺），或按 30nt 序列实时打分。分工原则：计算把 1,387 万候选筛到每基因个位数，实验做最后一公里。

**当前版本**：`v2.0-freeze`（2026-09-17）为交付基准；指标与变更的唯一权威记录是 `results/CHANGELOG_0927.md`。

## 目录结构

```
cs_pipeline/
├── env/
│   ├── environment.yml          # 主管线 conda 环境（crispr：py3.10 + R4.3 + genet）
│   ├── environment_demo.yml     # Streamlit demo 专用环境（grna-demo）
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
│   ├── app.py                   # Streamlit demo（两个 tab）
│   └── score_deepspcas9_cli.py  # Tab2 打分子进程入口（stdin 进、CSV 出）
├── demo/                        # demo 运行时数据（app_data.csv 等，由 prepare_demo_data.py 生成）
├── docs/                        # 项目资料库（索引见 docs/README.md）：plans/ 方案分工、
│                                #   reports/ 工作报告、knowledge/ 笔记、paper/ 文献、
│                                #   survey/ 调研、notification/ 赛事通知、_archive/ 存档
├── tools/                       # 外部工具（二进制与克隆不入 git，见「外部工具」）
├── README.md
└── requirements.txt
```

## 环境搭建（逐条命令，Windows + Anaconda Prompt / Git Bash）

```bash
# 1) 主管线环境（打分/特征/训练/扫描）
cd /d <本仓库所在目录>/cs_pipeline
conda env create -f env/environment.yml        # 环境名 crispr，py3.10 + R4.3 + genet 0.17.2
conda activate crispr

# 2) demo 专用环境（与 crispr 隔离：genet 锁 protobuf<3.20，与 streamlit 冲突）
conda env create -f env/environment_demo.yml   # 环境名 grna-demo，py3.10 + streamlit

# 3) CRISPRon 打分环境（WSL Ubuntu-22.04 内一次性组装，官方 TF2 仓库）
wsl -d Ubuntu-22.04 -- bash env/setup_crispron_wsl.sh
```

- Python 侧直接依赖见 `requirements.txt`（仅直接依赖，非 pip freeze 全量）。
- R 侧备用：`BiocManager::install("crisprScore")`（R≥4.3，安装脚本 `env/install_crisprscore.R`）。注：本项目实际打分链路为 genet（DeepSpCas9，Windows 原生）+ CRISPRon 官方仓库（WSL），crisprScore 仅备用——其 DeepSpCas9 依赖 py2.7+TF1.4.1 无 Windows 包，且任何版本均不含 CRISPRon。

## 复现流程（从 hitom_clean_v1.csv 到 demo，按 scripts/ 编号顺序）

```bash
conda activate crispr
python scripts/01_build_seq30.py        # 有坐标时：补 30bp 上下文 → data/hitom/hitom_seq30_0909.csv
# 坐标缺失时的实际执行路径：python scripts/01_build_seq30_cds.py（CDS 映射，内含自校验断言）
python scripts/02_score_deepspcas9.py   # DeepSpCas9 打分 → results/scores_deepspcas9_0910.csv
python scripts/03_score_crispron.py     # CRISPRon 打分（经 WSL）→ results/scores_crispron_0911.csv
python scripts/04_spearman_D2.py        # 迁移可行性 Spearman ρ → results/transferability_D2_0912.md
python scripts/05_features.py           # 特征矩阵 → results/feature_matrix_0913.csv
python scripts/06_train_stacking.py     # 按 gene_id 分组防泄漏训练 → results/meta_model_ridge_0919.joblib
python scripts/07_scan_lettuce.py       # 莴苣基因组基因区扫描 → results/ 候选表 + scan_stats
bash    scripts/08_casoffinder_run.sh   # Cas-OFFinder 脱靶（CPU）；GPU 分批见 scripts/run_mini_batches.ps1
python scripts/09_aggregate_offtarget.py# 汇总脱靶计数 → results/offtarget_counts_0924.csv
python demo/prepare_demo_data.py        # 合并 demo 数据 → demo/app_data.csv
conda run -n grna-demo streamlit run app/app.py   # 启动 demo（浏览器打开终端输出的 Local URL）
```

`00_consolidate_hitom.py` 为更上游的原始交付清洗合并脚本（data/raw/hitom_raw/ → data/hitom/hitom_clean_v1.csv），日常使用从 01 开始即可。模型训练完成后由 `scripts/predict.py` 的 `predict_efficiency(seq30_list)` 接口向 demo 供分。

## 模型与指标摘要

- **现行模型为全量重训版（`results/meta_model_ridge_full_0916.joblib`）**：487 行 / 14 基因 / 23 条 distinct guide，LOGO-CV 中位 ρ=0.414（未达 ρ≥0.5，如实）。权威文档：`results/model_card_full_0916.md`（特征顺序/训练数据/指标/局限）、`results/transferability_0917.md`（三体系迁移对照）、`results/model_comparison_full_0916.csv`。旧版 0919 模型及其指标（测试集 ρ=-0.344）已弃用留档。
- 复现路径：**全量版走 `scripts/10_rebuild_full_dataset.py` → `11` → `12` → `13`**（以改正版 xlsx 为源）；`scripts/01–06` 为 v1.x 冻结路径，仅用于复现历史产物。
- 当前可复现的实测锚点：
  - DeepSpCas9 链路：示例序列 `ATCGGCTAAGCTAGGCTAGCATCGTGGATC` 打分 71.2494（与基准 71.25 吻合，demo Tab2 可直接复现）；
  - 基因组扫描：45,770 基因、13,867,270 条候选、320 秒（`results/scan_stats_0923.md`）；
  - 脱靶：demo 范围 19,839 条 guide、6,088,827 个命中位点、mis3 脱靶中位数 16（`results/offtarget_runlog_0924.md`）。

## 外部工具

- **Cas-OFFinder v2.4.1**（2021-01-23 构建），Windows 64 位二进制；下载地址：https://github.com/snugel/cas-offinder （Releases 页 win64 包，解压得 `cas-offinder.exe` 置于 `tools/cas-offinder/`，不随代码包发布）。
- **CRISPRon / CRISPRoff**（RTH-tools，GPL/AGPL）：仓库克隆与模型文件不入 git，由 `env/setup_crispron_wsl.sh` 在 WSL 中重建（https://github.com/RTH-tools/crispron）。
- **genet 0.17.2**（pip）：DeepSpCas9 TF2 封装，随 `env/environment.yml` 安装；首次 predict 自动下载模型 checkpoint（约 700 KB，需联网）。

## 数据说明（未随代码发布的数据）

| 数据 | 原因 | 获取方式 |
|---|---|---|
| `data/reference_genomes/`（茎用生菜 v1.1c ~2.5 Gb、橡胶草 TKS ~1.2 Gb、莴苣 T2T ~2.5 Gb 及各自注释） | 体积过大 | 生菜两套由团队网盘提供；莴苣 T2T 在其论文 Figshare 页面下载 fasta/GFF3；`2-1_TKS.genome.fasta`/`3-1_LsT2T.*` 为 01/07 脚本的直接输入 |
| `data/lettuce/`（Cas-OFFinder 输入 + 着丝粒 bed） | 可再生 | `casoffinder_input.txt` 由 B2 候选生成（随 git 发布于 `data/lettuce/`）；着丝粒坐标出自莴苣 T2T 论文补充表 |
| `data/raw/`（Hi-TOM 原始测序交付 R0/R1 归档、PCR 检测图、合并源表、筛查序列） | 团队原始数据、体积大 | 团队共享网盘为权威源；`data/hitom/hitom_clean_v1.csv` 为清洗后快照，随代码发布 |
| `results/offtarget_raw_0924.txt`（399 MB 原始脱靶输出） | 体积过大、可再生 | 由 `scripts/run_mini_batches.ps1` + `scripts/09_aggregate_offtarget.py` 复现；汇总表 `offtarget_counts_0924.csv` 随代码发布 |
| CRISPRon 模型权重、genet checkpoint | 第三方模型文件 | 由上述安装步骤自动获取 |

## 匿名化说明

本仓库为匿名评审交付版本：全部 git 提交者为 `team <team@example.com>`；交付快照不含 `.git` 目录；源码、文档、配置中不含任何校名、院系名、师生姓名与个人路径（10.3 专项检查清单见团队工作报告）。
