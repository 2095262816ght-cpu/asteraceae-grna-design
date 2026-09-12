# 菊科菊苣族 CRISPR/Cas9 gRNA 设计工具（CS 管线）

一句话简介：以 DeepSpCas9 + CRISPRon 双模型打分经岭回归 Stacking 集成（自有植物 Hi-TOM 数据训练/验证）预测 gRNA 效率，扫描莴苣 T2T 基因组基因区产生候选，Cas-OFFinder 脱靶过滤，最终经 Streamlit demo 交付「按基因检索 / 按序列打分」两种用法。

## 目录结构

```
cs_pipeline/
├── env/
│   ├── environment.yml          # 主管线 conda 环境（crispr：py3.10 + R4.3 + genet）
│   ├── environment_demo.yml     # Streamlit demo 专用环境（grna-demo）
│   ├── environment_export_0909.yml  # crispr 环境完整导出（精确复现备查）
│   └── *.R / *.sh               # 备用安装与环境组装脚本（见「环境搭建」）
├── data/
│   ├── hitom_clean_v1.csv       # Hi-TOM 实测数据统一表（唯一权威输入）
│   ├── hitom_seq30_0909.csv     # 补齐 30bp 上下文后的主表
│   ├── demo_nlr50_candidates.csv# demo 范围候选（49 个 NLR 基因，19,839 条）
│   ├── casoffinder_input.txt    # Cas-OFFinder 输入（19,839 条 guide，错配≤3）
│   └── lettuce/                 # 莴苣 T2T 基因组 + GFF3 + 着丝粒 bed（不进 git，见「数据说明」）
├── scripts/                     # 流水线脚本，按编号顺序执行（见「复现流程」）
├── results/                     # 产出表、图、冻结文档（CHANGELOG_0927.md 为指标冻结记录）
├── app/
│   ├── app.py                   # Streamlit demo（两个 tab）
│   └── score_deepspcas9_cli.py  # Tab2 打分子进程入口（stdin 进、CSV 出）
├── demo/                        # demo 运行时数据（app_data.csv 等，由 prepare_demo_data.py 生成）
├── docs/                        # 各阶段工作报告与 demo 使用说明
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
python scripts/01_build_seq30.py        # 有坐标时：补 30bp 上下文 → data/hitom_seq30_0909.csv
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

`00_consolidate_hitom.py` 为更上游的原始交付清洗合并脚本（data/hitom_raw/ → hitom_clean_v1.csv），日常使用从 01 开始即可。模型训练完成后由 `scripts/predict.py` 的 `predict_efficiency(seq30_list)` 接口向 demo 供分。

## 模型与指标摘要

- 集成模型对比表 `results/model_comparison_0919.csv`（DeepSpCas9 单用 / CRISPRon 单用 / Stacking 集成的测试集 Spearman ρ、AUC、LOGO-CV 中位数）为本项目指标的唯一权威来源。**截至 v1.0-freeze（9.27）该表尚未随代码就位**，配套 `results/transferability_D2_0912.md`、`results/logo_cv_0916.csv` 同样待补；到位前本仓库不引用任何模型指标数字，冻结状态见 `results/CHANGELOG_0927.md`。
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
| `data/lettuce/`（莴苣 T2T 基因组 ~2.6 Gb + GFF3 + 着丝粒 bed） | 体积过大 | 莴苣 T2T 论文 Figshare 页面下载 fasta/GFF3；着丝粒坐标出自该论文补充表 |
| Hi-TOM 原始测序交付（`data/hitom_raw/`） | 团队原始数据 | 团队共享网盘为权威源；`data/hitom_clean_v1.csv` 为清洗后快照，随代码发布 |
| `results/offtarget_raw_0924.txt`（399 MB 原始脱靶输出） | 体积过大、可再生 | 由 `scripts/run_mini_batches.ps1` + `scripts/09_aggregate_offtarget.py` 复现；汇总表 `offtarget_counts_0924.csv` 随代码发布 |
| CRISPRon 模型权重、genet checkpoint | 第三方模型文件 | 由上述安装步骤自动获取 |

## 匿名化说明

本仓库为匿名评审交付版本：全部 git 提交者为 `team <team@example.com>`；交付快照不含 `.git` 目录；源码、文档、配置中不含任何校名、院系名、师生姓名与个人路径（10.3 专项检查清单见团队工作报告）。
