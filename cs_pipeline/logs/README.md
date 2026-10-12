# 训练 / 验证日志与随机种子记录（logs/）

> 对应《附件5 代码提交要求》第二节「必备文件与脚本要求」与第三节「可复现性与溯源要求 — 训练」。
> 本项目未采用逐次运行落盘的文本日志文件，而是以**指标冻结记录 + 折级明细表 + 运行审计日志**的形式归档，全部位于 `../results/`，本目录仅作索引。

## 一、训练与验证日志

| 内容 | 文件 | 说明 |
|---|---|---|
| 指标冻结与变更权威记录 | [`../results/CHANGELOG_0927.md`](../results/CHANGELOG_0927.md) | 自 9.09 起逐日逐条记录数据治理、模型训练、指标重跑与决策会签全过程（约 33 KB） |
| 生产模型训练产物与折级明细 | [`../results/folds_hier_bb_nob879_0921.csv`](../results/folds_hier_bb_nob879_0921.csv)、[`../results/metrics_hier_bb_nob879_0921.csv`](../results/metrics_hier_bb_nob879_0921.csv) | 16 折 LOGO-CV 逐折 ρ / p 值 / 有效折判定 |
| 同口径三方模型横向对比 | [`../results/model_comparison_nob879_0921.csv`](../results/model_comparison_nob879_0921.csv)、[`../results/model_comparison_nob879_folds_0921.csv`](../results/model_comparison_nob879_folds_0921.csv)、[`../results/model_comparison_nob879_report_0924.md`](../results/model_comparison_nob879_report_0924.md) | Anchor / Method A2 / 形态二 对比与可比性分析 |
| 批次效应诊断 | [`../results/b_audit_0919.md`](../results/b_audit_0919.md)、[`../results/b_audit_0920.md`](../results/b_audit_0920.md)、[`../results/b_batch_effect_fold_details_0921.csv`](../results/b_batch_effect_fold_details_0921.csv) | 批次位移、锚点分布、EB 收缩诊断 |
| 敏感性验证 | [`../results/sensitivity_dual_grna_folds_0924.csv`](../results/sensitivity_dual_grna_folds_0924.csv)、[`../results/sensitivity_dual_grna_summary_0924.csv`](../results/sensitivity_dual_grna_summary_0924.csv) | 双 gRNA 错配样本剔除敏感性（ρ 波动 -0.0010） |
| 全基因组扫描运行记录 | [`../results/scan_stats_0923.md`](../results/scan_stats_0923.md) | 45,770 基因 / 13,867,270 条候选 / 320 秒 |
| 脱靶检索运行审计 | [`../results/offtarget_runlog_0924.md`](../results/offtarget_runlog_0924.md) | Cas-OFFinder 口径、命中统计、着丝粒抑制区过滤 |

## 二、随机种子设置

**统一随机种子：`random_state=42`**（全队约定，跨脚本一致）。

| 脚本 | 用途 | 种子位置 |
|---|---|---|
| `scripts/15_train_hierarchical_bb_nob879.py` | 生产模型训练 | `GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)` |
| `scripts/24_model_comparison_nob879.py` | 同口径模型对比 | `RANDOM_STATE = 42`（顶部文档字符串明记） |
| `scripts/25_sensitivity_dual_grna_0924.py` | 敏感性验证 | `RANDOM_STATE = 42` |
| `scripts/06_train_stacking.py` / `13_features_train_full.py` / `14_public_mix_train.py` | 历史链路 | 同上 |

LOGO-CV（留一基因交叉验证）为确定性划分，不含随机性。

## 三、运行硬件与耗时

| 环节 | 硬件 | 耗时 |
|---|---|---|
| 全基因组候选扫描（`07_scan_lettuce.py`） | 64 位多核 CPU，内存 ≥16 GB | **320 秒**（45,770 基因 / 1,386.7 万候选） |
| 生产模型训练（`15_train_hierarchical_bb_nob879.py`） | CPU，无需 GPU | 数分钟级 |
| Cas-OFFinder 脱靶检索 | CPU 分批（`run_mini_batches.ps1`）或可选 GPU | 数小时级，demo 范围 19,839 条 guide / 608 万命中 |
| DeepSpCas9 / CRISPRon 打分 | CPU（`torch==2.14.0+cpu`、`tensorflow==2.9.3`，无 CUDA 依赖） | 批量打分随规模线性增长 |

详见 [`../README.md`](../README.md)「运行环境要求」。
