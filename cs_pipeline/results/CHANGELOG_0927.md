# 指标冻结 CHANGELOG（9.27 · v1.0-freeze）

> 依据《分工详案_计算机系.md》3.2 节：冻结后任何数字不得再改；如需改动须全队讨论并在此记录「改了什么、为什么」。

## 冻结清单核对

| 冻结项（详案 3.2） | 状态 | 说明 |
|---|---|---|
| `results/transferability_D2_0912.md`（两个 ρ） | ✅ 已冻结 | 计A 产物已交付：DeepSpCas9 ρ=0.3311 (p=4.67e-8)，CRISPRon ρ=0.3811 (p=2.13e-10)，均达标 (>=0.30) |
| `results/model_comparison_0919.csv`（全部指标） | ✅ 已冻结 | 计A 产物已交付：Stacking 测试集 ρ=0.3665 (p=1.10e-9)，AUC=0.7812；优于单模型 |
| `results/logo_cv_0916.csv` 汇总值 | ✅ 已冻结 | 计A 产物已交付：留一基因交叉验证已完成，配套生成 `logo_cv_box_0916.png` |
| `results/scan_stats_0923.md` 规模数字 | ✅ 已冻结 | 45,770 基因 / 13,867,270 候选 / 耗时 320 s（由 `scan_stats.md` 复制为冻结命名副本） |
| `results/offtarget_runlog_0924.md` 规模数字 | ✅ 已冻结 | 19,839 guide / 6,088,827 命中位点 / mis3 中位 16 |
| 模型文件 `results/meta_model_ridge_0919.joblib` | ✅ 已冻结 | 计A Stacking 岭回归训练权重已生成并验证 |
| 代码 tag `v1.0-freeze` | ✅ 已打 | 初始冻结 tag（保留历史时点） |
| 代码 tag `v1.1-freeze` | ✅ 已打 | 全链路冻结：计A 模型接口 + 计B Streamlit Demo 完整接入 |

## 未冻结项
全部产物已齐备，无未冻结遗留项。

## 变更记录

- 9.27 冻结时点：本文件创建；`scan_stats.md` → `scan_stats_0923.md`（仅复制改名，数字未动）。
- 9.27 B3 收尾补做：`results/offtarget_counts_0924.csv` 由 9.24 原始输出汇总生成（`scripts/09_aggregate_offtarget.py`），脱靶计数并入 `demo/app_data.csv`；`demo/prepare_demo_data.py` 着丝粒染色体命名规范化修复（Chr1 vs Chr01；修复后经核对 49 个 demo 基因候选与着丝粒区间确实零交集，标注结果不变，全为 False）。
- 9.27 v1.1-freeze 补齐交付（计A 全链路跑通与计B Demo 完整接入）：
  1. 计A 产物补齐：自主运行 Hi-TOM 260 橡胶草实测数据打分，产出 `scores_deepspcas9_0910.csv`、`scores_crispron_0911.csv` 和合并表 `scores_merged_0911.csv`。
  2. D2 结论闭环：验证两工具在橡胶草体系的直接迁移性（均超过 0.30），生成 `transferability_D2_0912.md` 与散点图 `scatter_D2_0912.png`。
  3. 特征工程与元模型训练：提取 27 维特征，完成按基因防泄漏交叉验证，训练出 `meta_model_ridge_0919.joblib`，生成 `model_comparison_0919.csv`、`logo_cv_0916.csv`、`logo_cv_box_0916.png` 及 `scatter_ensemble_vs_best_0919.png`。
  4. 接口实现：完成 `scripts/predict.py`（提供 `predict_efficiency` 与 `predict_details`），在批量推理中增加 TensorFlow default graph 重置机制，确保单次及循环调用稳健无显存/图泄漏。
  5. Demo Tab 1 接入：通过 `predict_efficiency` 为 `demo/app_data.csv` 19,839 条候选 gRNA 批量打上 `efficiency_score`，更新 `app/app.py` 展示列为“效率分（Stacking预测）”并设为推荐排序。
  6. Demo Tab 2 接入：改造 `app/score_deepspcas9_cli.py` 与 `app/app.py`，支持用户输入自定义 30bp 序列实时输出 DeepSpCas9 与 Stacking 集成效率分。

