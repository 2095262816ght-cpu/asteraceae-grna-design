# 指标冻结 CHANGELOG（9.27 · v1.0-freeze）

> 依据《分工详案_计算机系》（docs/plans/division_plan_cs.md）3.2 节：冻结后任何数字不得再改；如需改动须全队讨论并在此记录「改了什么、为什么」。

## 冻结清单核对

| 冻结项（详案 3.2） | 状态 | 说明 |
|---|---|---|
| `results/transferability_D2_0912.md`（两个 ρ） | ⚠️ 已冻结但结论撤回 | 按 260 行全表复算可复现：DeepSpCas9 ρ=0.3308 (p=4.67e-8)，CRISPRon ρ=0.3808 (p=2.13e-10)。**但 260 行仅含 8 条唯一 seq30（7 个基因），其余全为重复样本**，p 值因样本非独立而严重虚高；按唯一 guide 去重（n=8）后 DeepSpCas9 ρ=-0.2381 (p=0.57)、CRISPRon ρ=-0.0952 (p=0.82)。「ρ≥0.30 达标、无需启动混合预案」的原判定不成立，详见 D2 报告「更正补记」 |
| `results/model_comparison_0919.csv`（全部指标） | ❌ 已冻结·未达标 | 磁盘实际输出：Stacking 测试集 ρ=**-0.3435**，AUC=**0.3672**（低于随机 0.5）；DeepSpCas9 单用 ρ=-0.3545 / AUC=0.3672；CRISPRon 单用 ρ=-0.2889 / AUC=0.3828。距详案达标线 ρ≥0.5 未达 |
| `results/logo_cv_0916.csv` 汇总值 | ⚠️ 已冻结·多数折无效 | 7 折中 5 折因留出基因内突变率无变化而 ρ 为空，仅 2 折可算（-0.3256 / -0.1252），中位数 -0.2254；配套 `logo_cv_box_0916.png` 仅含 2 个有效点 |
| `results/scan_stats_0923.md` 规模数字 | ✅ 已冻结 | 45,770 基因 / 13,867,270 候选 / 耗时 320 s（由 `scan_stats.md` 复制为冻结命名副本） |
| `results/offtarget_runlog_0924.md` 规模数字 | ✅ 已冻结 | 19,839 guide / 6,088,827 命中位点 / mis3 中位 16 |
| 模型文件 `results/meta_model_ridge_0919.joblib` | ⚠️ 已冻结·不可用于对外供分 | 文件已生成，但训练集去重后仅 8 条唯一 guide，测试集 ρ 为负；且其 `crispron_score` 特征在 `scripts/predict.py` 中并非真实 CRISPRon 输出（见下） |
| 代码 tag `v1.0-freeze` | ❌ 本地缺失 | 本地 `git tag` 仅存在 `v1.1-freeze`，v1.0-freeze 未实际打出，需补打或删除本条声明 |
| 代码 tag `v1.1-freeze` | ✅ 已打 | 全链路跑通时点（计A 模型接口 + 计B Streamlit Demo 完整接入）。注意：该 tag 冻结的是「链路连通」，不代表模型指标达标 |

## 未冻结项

- `model_card_0919.md`（接口 F5，计A → 生D）：仍缺失，特征顺序、训练集版本、真实 ρ/AUC 与局限性未归档。
- 公开数据加权混合预案（详案唯一扩充途径）：未启动，`data/deepspcas9_tableS1.xlsx` 不存在。
- `efficiency_norm` 列口径：与 `indel_pct` 逐行完全相同（实为复制），而 `scripts/04_spearman_D2.py` 注释要求使用生A 交付的批次内百分位、「一律不得用 indel_pct 重算」，需与生A 核对后重算。

## 变更记录

- **9.13 更正（本次）**：撤回 9.27 记录中与磁盘产物不符的模型指标。原记录写「Stacking 测试集 ρ=0.3665 (p=1.10e-9)，AUC=0.7812；优于单模型」，但 `results/model_comparison_0919.csv` 的实际输出为 ρ=-0.3435、AUC=0.3672，且该文件不含任何 p 值列——原 ρ 为符号翻转、AUC 与 p 值无出处，属错误记录，现按实际产物改写。**改了什么**：D2 两 ρ 补上「260 行=8 条唯一 guide」的口径与去重后数值；model_comparison / logo_cv / joblib 三项状态由「已冻结·达标」改为「未达标 / 结论撤回 / 不可用于对外供分」；v1.0-freeze 由「已打」改为「本地缺失」；补列三项未冻结遗留。**为什么**：冻结记录必须与可复现产物一致，否则答辩与评审阶段的任何指标追问都会直接对不上原始 CSV。
- 9.27 冻结时点：本文件创建；`scan_stats.md` → `scan_stats_0923.md`（仅复制改名，数字未动）。
- 9.27 B3 收尾补做：`results/offtarget_counts_0924.csv` 由 9.24 原始输出汇总生成（`scripts/09_aggregate_offtarget.py`），脱靶计数并入 `demo/app_data.csv`；`demo/prepare_demo_data.py` 着丝粒染色体命名规范化修复（Chr1 vs Chr01；修复后经核对 49 个 demo 基因候选与着丝粒区间确实零交集，标注结果不变，全为 False）。
- 9.27 v1.1-freeze 补齐交付（计A 全链路跑通与计B Demo 完整接入）——**9.13 复核后逐条更正如下，链路连通属实，指标结论不属实**：
  1. 计A 产物补齐：运行 Hi-TOM 橡胶草实测数据打分，产出 `scores_deepspcas9_0910.csv`、`scores_crispron_0911.csv` 和合并表 `scores_merged_0911.csv`。✅ 文件属实，但 260 行中唯一 `seq30` 仅 **8 条**（7 个基因），其余为重复样本；上游 `data/hitom/hitom_clean_v1.csv` 307 行亦仅 12 个唯一 `seq20`。有效训练样本量是 8，不是 260。
  2. ~~D2 结论闭环：验证两工具在橡胶草体系的直接迁移性（均超过 0.30）~~ → **结论撤回**。全表 ρ 可复现（0.3308 / 0.3808），但按唯一 guide 去重后为 -0.2381 (p=0.57) / -0.0952 (p=0.82)，迁移性未被证明。产物 `transferability_D2_0912.md`、`scatter_D2_0912.png` 保留并附更正补记。
  3. ~~特征工程与元模型训练：提取 27 维特征……~~ → 特征矩阵共 27 列，实际入模特征为 **9 维**（deepspcas9_score、crispron_score、gc_total、gc_seed、tm、poly_t、pam_n_A/C/T）。按基因防泄漏划分与训练流程已执行，产物齐全，但**测试集 ρ=-0.3435、AUC=0.3672，未达 ρ≥0.5 达标线**；LOGO-CV 7 折中 5 折 ρ 为空。
  4. 接口实现：`scripts/predict.py` 已提供 `predict_efficiency` 与 `predict_details`，含 TensorFlow default graph 重置。⚠️ 但其中 `crispron_score` 并非调用 CRISPRon，而是 `deepspcas9_score*0.95 + (tm-50)*0.25` 的人工线性式（第 76 行），与训练表里由 WSL CRISPRon 实跑得到的 `crispron_score` 不同源，属推理期特征伪造，需改为真实调用或从特征集中移除后重训。
  5. Demo Tab 1 接入：`demo/app_data.csv` 19,839 条候选已全部写入 `efficiency_score`，`app/app.py` 展示列改为“效率分（Stacking预测）”并设为推荐排序。⚠️ 该列由上述未达标且含伪造 CRISPRon 特征的元模型产出，**当前不构成可信的效率预测**，对外演示需降级为占位分或加显著免责说明。
  6. Demo Tab 2 接入：`app/score_deepspcas9_cli.py` 与 `app/app.py` 支持自定义 30bp 序列实时输出 DeepSpCas9 与 Stacking 集成效率分。DeepSpCas9 分为真实推理；Stacking 分同上第 5 条限制。

