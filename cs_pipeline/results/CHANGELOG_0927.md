# 指标冻结 CHANGELOG（9.27 · v1.0-freeze）

> 依据《分工详案_计算机系.md》3.2 节：冻结后任何数字不得再改；如需改动须全队讨论并在此记录「改了什么、为什么」。

## 冻结清单核对

| 冻结项（详案 3.2） | 状态 | 说明 |
|---|---|---|
| `results/transferability_D2_0912.md`（两个 ρ） | ❌ 未交付 | 计A 产物，截至冻结时点不存在，见下「未冻结项」 |
| `results/model_comparison_0919.csv`（全部指标） | ❌ 未交付 | 计A 产物（Stacking 评估），不存在 |
| `results/logo_cv_0916.csv` 汇总值 | ❌ 未交付 | 计A 产物（LOGO-CV），不存在 |
| `results/scan_stats_0923.md` 规模数字 | ✅ 已冻结 | 45,770 基因 / 13,867,270 候选 / 耗时 320 s（由 `scan_stats.md` 复制为冻结命名副本） |
| `results/offtarget_runlog_0924.md` 规模数字 | ✅ 已冻结 | 19,839 guide / 6,088,827 命中位点 / mis3 中位 16 |
| 代码 tag `v1.0-freeze` | ✅ 已打 | 见 git tag（附注说明未冻结项） |

## 未冻结项（依赖计A 交付，阻塞记录）

计A 的 Stacking 集成模型链路（D2 ρ 结论、模型对比表、LOGO-CV）截至 9.27 未产出任何结果文件，`scripts/predict.py` 仍为 NotImplementedError 占位。上述三项到位后需补打冻结（建议以 `v1.1-freeze` 追加 tag 并在此 CHANGELOG 记录）。

## 变更记录

- 9.27 冻结时点：本文件创建；`scan_stats.md` → `scan_stats_0923.md`（仅复制改名，数字未动）。
- 9.27 B3 收尾补做：`results/offtarget_counts_0924.csv` 由 9.24 原始输出汇总生成（`scripts/09_aggregate_offtarget.py`），脱靶计数并入 `demo/app_data.csv`；`demo/prepare_demo_data.py` 着丝粒染色体命名规范化修复（Chr1 vs Chr01；修复后经核对 49 个 demo 基因候选与着丝粒区间确实零交集，标注结果不变，全为 False）。
