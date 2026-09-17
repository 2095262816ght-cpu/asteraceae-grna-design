# Model Card — Stacking gRNA 效率模型（full_0916）

> 接口 F5（计A → 生D）。本文档是 `results/meta_model_ridge_full_0916.joblib` 的唯一权威说明。
> 旧版 `meta_model_ridge_0919.joblib` 的 model card 从未交付（见 CHANGELOG_0927 未冻结项），且该模型已弃用（LOGO-CV ρ=-0.225），勿再使用。
> 更新日期：2026-09-16

## 1. 模型身份

| 项 | 值 |
|---|---|
| 文件 | `results/meta_model_ridge_full_0916.joblib` |
| 类型 | Ridge（岭回归）stacking 元模型，输入含两个公开模型的打分 |
| 超参 | alpha=316.23（训练集内 GroupKFold + GridSearchCV 选出，MSE 准则）；solver="svd"（见 §5 注） |
| 输出 | 效率分，与 indel_pct×100 同尺度；接口侧 clip 到 [0, 100] |
| 调用入口 | `scripts/predict.py::predict_efficiency(seq30_list)`（计B 只调此函数） |

## 2. 输入约定（极易踩坑，务必逐字遵守）

- 输入为 **30nt 序列**：`4nt 上游 + 20nt guide + 3nt PAM + 3nt 下游`（沿 guide 5'→3' 方向，仅 ACGT，大写）。
- PAM 必须为 NGG；训练数据只覆盖首碱基 A/C/T 的 PAM（无 GGG 样本），GGG 的 guide 三个 pam_n 特征全 0，属训练分布外输入，分数可信度更低。
- 特征共 **9 维，顺序固定**（错序 = 垃圾输出）：

| # | 特征 | 计算 |
|---|---|---|
| 1 | deepspcas9_score | genet `SpCas9().predict(seq30)` |
| 2 | crispron_score | 真实 CRISPRon（WSL，tools/CRISPRon）；**predict.py 运行时为近似公式，见 §5** |
| 3 | gc_total | seq20 的 GC 含量 |
| 4 | gc_seed | seq30 第 19–24 位（PAM 近端 6nt）的 GC 含量 |
| 5 | tm | seq20 的 Tm_NN（Biopython，最近邻法） |
| 6 | poly_t | seq20 含 "TTTT" 记 1，否则 0 |
| 7–9 | pam_n_A / pam_n_C / pam_n_T | PAM 首碱基 one-hot |

## 3. 训练数据

- 来源：`data/1_Hi-results-12-20260913.xlsx`（含 2026-09-15/16 全部更正：5712 序列更正、6995/6999 窗口更正、strand 221 行、坐标 1bp、PAM CCA→ACT、5712 indel 口径写回；详见 `docs/problem.md` / `docs/problem2.md`）。
- 规模：**487 行 / 14 个基因 / 23 条 distinct guide**（491 行剔 4 行非 NGG）。
- 批次：USR-8145(112)、USR-4411(109)、USR-5713(86)、USR-23709(68)、USR-5712(61)、USR-25902(45)、USR-26162(6)。
- 标签：`efficiency_norm = indel_pct × 100`（indel_pct 为 Hi-TOM 实测切割侧非 WT reads 占比；5712 批 61 行为右侧口径，其余为左侧口径）。
- seq30 上下文：415 行来自 CDS，72 行（靶点在内含子/基因间区）来自基因组坐标。
- 防泄漏：所有划分/LOGO 按基因分组，LG01.6995 与 LG01.6999（同源拷贝）合并为同一分组，共 13 组。
- 训练脚本：`scripts/10~13`（10 重建数据、11 DeepSpCas9、12 CRISPRon、13 特征+训练）。

## 4. 性能（全部如实，勿选择性引用）

| 评估 | 值 | 说明 |
|---|---|---|
| **LOGO-CV 中位 Spearman ρ** | **0.414** | 13 折中 7 折可定义：LG07.3296 0.68、LG02.4013 0.65、LG07.3933 0.42、LG02.4820 0.41、LG01.8265 0.22、LG01.6995/6999 0.08、LG01.555 -0.32；6 折因留出基因只有 1 条 guide（组内无排序信号）无法定义 |
| 外层测试折 ρ / AUC | -0.676 / 0.074 | 仅 3 个留出基因（LG01.555、LG05.2111、LG07.3296），含开关式标签基因，单折噪声极大，不作结论依据 |
| 样本内 guide 级（23 条）ρ | 0.402 | 回判非独立评估，仅作 sanity anchor |
| 达标线（详案 ρ≥0.5） | **未达** | 旧版（260 行/7 基因）LOGO-CV 为 -0.225，本版显著改善但仍未达标 |

## 5. 已知局限（使用前必读）

1. **根本瓶颈是 guide 多样性**：23 条 distinct guide / 14 基因，8 个基因只有 1 条 guide。再堆同一 guide 的重复行不会提升。
2. **已知病态**：① deepspcas9_score 系数为负（-4.33，与 crispron_score 共线性 artifact，不代表 DeepSpCas9 分越高效率越低）；② 内含子/基因间区靶点（如 5712 的 GAAA guide）会被严重误判——该 guide 实测 indel≈100，模型给 0 分；③ 开关式标签（0 与 100 两极）的基因上排序不可靠。
3. **predict.py 运行时的 crispron_score 是近似公式**（`deep×0.95+(tm-50)×0.25`），与训练特征不同源；批量精确打分请走 `demo/rescore_demo_full_0916.py`（真实 CRISPRon）。
4. **demo 的 `efficiency_score_full_0916` 列可供内部参考排序，对外演示须附带"模型未达标（LOGO-CV ρ=0.414）"的说明**，立场同 CHANGELOG_0927。
5. solver="svd" 是为规避本机 scipy 1.15.2 cholesky 崩溃的等价替代（当日已降级 scipy 1.14.1 根治）；对解无实质影响。
6. 体系外推警告：训练数据全部来自橡胶草（TKS）Hi-TOM；用于生菜（LsT2T）候选打分属跨物种迁移，假设"序列→效率"关系保守，未经验证。
7. **公开数据混合已证无效**（2026-09-17，详案预案已执行）：2.4 万条人源数据按 50:1~5000:1 加权混合，LOGO-CV 均不超过本模型（详见 `results/mixed_weight_sensitivity_0917.csv` 与 CHANGELOG 9-17 条）。本模型即为最终版，不会再有更好的权重配置。

## 6. 产物清单

| 产物 | 路径 |
|---|---|
| 模型 | `results/meta_model_ridge_full_0916.joblib` |
| 指标 | `results/model_comparison_full_0916.csv`、`results/logo_cv_full_0916.csv` |
| 特征矩阵 | `results/feature_matrix_full_0916.csv`（487×28） |
| 图 | `results/logo_cv_box_full_0916.png` |
| demo 重打分 | `demo/app_data.csv` 的 `efficiency_score_full_0916` 列（备份 `demo/app_data.backup_20260916_pre_rescore.csv`） |
| 训练中间产物 | `data/hitom/hitom_clean_full_0916.csv`、`hitom_seq30_full_0916.csv`、`results/scores_*_full_0916.csv` |
