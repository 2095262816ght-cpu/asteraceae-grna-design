# 菊科菊苣族 gRNA 设计工具项目进展全景审计报告

> **依据文档**：
> - [`docs/plans/project_plan_v3_condensed_0907.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/project_plan_v3_condensed_0907.md)（主方案）
> - [`docs/plans/division_plan_master.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_master.md)（甘特图与接口规范）
> - [`docs/plans/division_plan_cs.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_cs.md)（技术实施标准）
> - [`docs/problem.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem.md) / [`docs/problem2.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem2.md)（9.14–9.16 数据表检查与更正全过程）
> - [`results/CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md)（冻结记录，含 9.13 / 9.16 两段更正）
> - [`results/model_card_full_0916.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/model_card_full_0916.md)（现行模型卡，接口 F5）
> - 计算机系流水线全量代码与产物目录：[`cs_pipeline/`](file:///d:/lifesciencechallenge/cs_pipeline/)
>
> **审计基准时点**：2026-09-21 复核（最新 commit `9b36e26`；9.18 数据扩充至 1368 行、9.19 老师裁决落地、9.20–9.21 打分版 14/15/16/16.1 交付链与两轮独立审计已完成，现行口径见**第六节**。第一至五节中所有 ρ=0.414 / 487 行数字为 0916 旧口径，保留存档）
>
> **📌 9.21 更新要点**：①数据基线 487 行 → **1368 行 / 24 批次**（NEWdata 877 行 9.18 并入主表，NEWdata 目录 9.21 经 MD5 核验并入 `data/raw/hitom/NEWdata_0918/` 后撤销）；②**9.19 老师裁决**落地为唯一剔除口径（360 行：QC 253 + USR-14333 整批 87 + USR-22807 整批 20；5448/6137 QC 撤销），现行交付版 **16.1**：1368 = 训练集 969 + 不可打分 3 + 裁决剔除 360 + 弱信号待追认 36（969+36=1005 与锚定口径闭环）；③指标更新：扩表后 LOGO-CV 中位 ρ 由 0.414（487 行旧口径，且对 indel=1 行敏感：去掉即 0.596）降至裁决后 1005 行的 -0.078（锚定）/ -0.220（raw）；**16.1 训练集 969 行（剔弱信号 36 行）锚定 LOGO 回升至 +0.310（现行最好数字）**，**ρ≥0.5 仍未达标**，结构性瓶颈仍是 guide 多样性（969 行训练集仅 36 个 distinct 分数对，最大并列组 239 行）；④15 版经独立审计发现两个阻断问题（效率分 tie-break 抖动、9.19 裁决未落地），已在 16/16.1 版修复（`results/b_audit_0920.md`）；guide候选表已回传并 100% 复推验证 15 版 219 行分级。
>
> **📌 9.17 更新要点**：自 9.13 复核以来发生三件大事——①数据表完成系统性检查与更正（`problem.md` / `problem2.md`），487 行 / 14 基因 / 23 条 distinct guide 全部纳入训练（原 260 行 / 7 基因 / 8 条唯一 guide）；②全量重跑后 LOGO-CV 中位 ρ 由 -0.225 升至 **+0.414**，**仍未达 ρ≥0.5 达标线**；③接口 F5 模型卡已补（`model_card_full_0916.md`），demo 19,839 条候选已用**真实**双模型重打分（新列 `efficiency_score_full_0916`）。旧版（0919 冻结）模型与结论全部弃用留档。

---

## 一、执行摘要：我们在哪里？

工程链路（计B）已闭环且指标可信；算法链路（计A）经 9.14–9.16 数据更正与全量重跑后**显著改善但仍未达标**：LOGO-CV 中位 ρ=0.414（达标线 ρ≥0.5），结构性瓶颈是 guide 多样性（23 条 / 14 基因，8 个基因仅 1 条 guide），不是行数或调参。

```mermaid
graph TD
    classDef done fill:#d4edda,stroke:#28a745,color:#155724;
    classDef bad fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef pend fill:#fff3cd,stroke:#ffc107,color:#856404;

    A[阶段0: 数据清洗与环境搭建]:::done --> B[阶段1: 预训练模型打分与D2可行性]:::bad
    B --> C[阶段2: Stacking岭回归训练与评估]:::pend
    C -->|F4 predict.py 已切换全量模型| D[阶段3: 莴苣工具化与Streamlit Demo]:::done
    D --> E[阶段4: 成果冻结与交付冲刺]:::pend

    subgraph 计B负责: 已闭环且指标可信
        D
        F[全外显子/启动子扫描 13.87M]:::done
        G[Cas-OFFinder 脱靶 6.08M]:::done
        H[Streamlit 双Tab交互与截图]:::done
        I[10.3 匿名化检查与代码打包]:::done
    end

    subgraph 计A负责: 改善但未达标 🟡
        B
        C
        J[全量重跑: 487行/23条guide/14基因]:::pend
        K[D2 迁移 ρ: 去重后为负且不显著]:::bad
        L[Stacking LOGO-CV 中位 ρ=0.414 未达标]:::pend
    end
```

### 核心结论速览
1. **计B（工程与工具链）维持 10.3 交付状态，指标可信**：
   - 莴苣 T2T 全基因组 45,770 基因扫描完成（13,867,270 条候选）；
   - Cas-OFFinder 本地脱靶预测完成（19,839 条 demo gRNA，608 万脱靶位点）；
   - Streamlit demo 界面、预制数据、7 张演示截图、使用说明全部就绪；
   - 9.27 指标冻结记录、代码打包规范、10.3 匿名化专项检查（零命中）已全部做完。
2. **计A（算法模型链条）9.14–9.16 完成数据更正 + 全量重跑，改善但未达标**：
   - **数据更正**（`problem.md` / `problem2.md`）：5712 批 61 行序列更正（真实 guide 为负链 `GAAAATGTCAGGATGCCTGA`+AGG）并将 indel_pct 写回切割点侧口径真实值（中位 0.0123→1.0）；6995/6999 批 32 行窗口移位 5bp 更正；strand 列 221 行 `-`→`+`；LG02.4820 四行 PAM CCA→ACT；CATT guide 坐标 1bp 改正；
   - **全量重跑**（`scripts/10~13`，产物带 `_full_0916` 后缀，9.x 冻结产物一律未动）：487 行 / 14 基因 / 13 分组（LG01.6995/6999 同源合并防泄漏），72 行内含子/基因间区靶点回退基因组坐标取 seq30；
   - **指标**：LOGO-CV 中位 ρ 由 -0.2254 → **+0.4140**（7/13 折可定义，最高 LG07.3296 0.68、LG02.4013 0.65）；外层测试折 ρ=-0.676（仅 3 个留出基因、噪声极大，不作结论依据）；样本内 guide 级回判 ρ=0.402；**仍未达 ρ≥0.5 达标线**；
   - **已知病态（模型卡如实记录）**：deepspcas9 特征系数为负（共线性 artifact）；5712 的 GAAA guide（内含子位点）样本内被误判为 0 分；开关式标签基因排序不可靠；
   - **瓶颈定性**：14 个基因中 8 个只有 1 条 distinct guide——特征全部由序列派生，单 guide 基因内无排序信号（6 折 LOGO 无法定义 ρ）。要提升必须增加**不同序列的 guide**（详案规定的公开数据加权混合预案），堆重复行无效；
   - 旧版 0919 模型（测试集 ρ=-0.3435 / AUC=0.3672）已弃用留档，勿再使用。

---

## 二、全员里程碑与甘特表逐项对比（阶段 0 – 阶段 4）

### 阶段 0：数据盘点 + 环境准备（9.7 – 9.9 · 计划工时 9h）
**目标**：Hi-TOM 数据清洗定档 D1，conda 环境装配，验证预训练单序列打分。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| Hi-TOM 原始数据清洗与 12 列规范 | 生A | 9.8 晚 | ✅ 已完成 | 产出 [`cs_pipeline/data/hitom/hitom_clean_v1.csv`](file:///d:/lifesciencechallenge/cs_pipeline/data/hitom/hitom_clean_v1.csv)（307 行有效数据，剔除 113 行空白，空 guide_id 已补全）。 |
| **数据表系统性检查与更正（9.14–9.16 新增专项）** | 计A | — | ✅ 已完成 | `data/1_Hi-results-12-20260913.xlsx` 全表核查：23 条 distinct guide 逐条回 TKS 基因组比对，序列/坐标/链向/PAM 全部自洽；完成 strand 列（221 行）、5712 批序列+indel 口径（61 行）、6995/6999 窗口移位（32 行）、PAM CCA→ACT（4 行）、坐标 1bp 等更正，每次更正均有备份与脚本留痕。全过程见 [`docs/problem.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem.md)（历史）与 [`docs/problem2.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem2.md)（现状）；唯一欠缺的外部证据（oligo 合成记录）9.16 已按现有证据链定稿，不阻塞下游。 |
| 补齐 30bp 上下文序列 | 计A | 9.9 晚 | ✅ 已完成（9.16 全量重建） | 旧产物 `hitom_seq30_0909.csv`（260 行）；9.16 全量重建产物 `data/hitom/hitom_seq30_full_0916.csv`（487/487 全命中：415 CDS + 72 基因组坐标回退）。 |
| conda 主环境与 demo 环境搭建 | 计A / 计B | 9.9 晚 | ✅ 已完成 | `crispr`（py3.10+genet+TF2.9）与 `grna-demo` 环境已分离；CRISPRon Windows 原生路线与 WSL 路线均通。9.16 事故修复：crispr 环境 scipy 1.15.2 cholesky 路径本机硬崩，已降级 1.14.1 根治；`env/run_crispron_wsl.sh` 旧路径已修。 |
| 示例序列打分验证 | 计A | 9.9 晚 | ✅ 已完成 | DeepSpCas9 打出 71.2494（基准 71.25）；CRISPRon 原生打出 59.61（341 条官方测试逐字节一致）。 |
| **决策点 D1（路线定档）** | 全员 | 9.8 晚 | ✅ 已定案 | 有效数据 307 条（可打分 260 条），卡在 $\ge 300$ 条边缘。团队定案走**纯 Stacking**，不碰复杂的神经网络微调。9.16 全量重建后升至 487 行 / 14 基因。 |

---

### 阶段 1：预训练模型批量打分 + 迁移可行性 D2（9.10 – 9.12 · 计划工时 9h）
**目标**：用两个预训练模型给自有橡胶草数据打分，评估其在植物上的迁移相关系数（Spearman $\rho$）。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| DeepSpCas9 批量打分 | 计A | 9.10 | ✅ 已产出（9.16 重打） | 旧产物 `results/scores_deepspcas9_0910.csv`（260 行）；全量版 `results/scores_deepspcas9_full_0916.csv`（487 行，`scripts/11_score_deepspcas9_full.py`）。 |
| CRISPRon 批量打分 | 计A | 9.11 | ✅ 已产出（9.16 重打） | 旧产物 `results/scores_crispron_0911.csv`（260 行，WSL 实跑）；全量版 `results/scores_crispron_full_0916.csv`（`scripts/12_score_crispron_full.py`），合并表 `scores_merged_full_0916.csv`。 |
| 预备公开数据集 Table S1 | 计A | 9.11 | ❌ 未入库 | `cs_pipeline/data/deepspcas9_tableS1.xlsx` 仍不存在；瓶颈定性为 guide 多样性后，该混合预案是**唯一尚未启动的达标途径**（见第五节 P0）。 |
| **决策点 D2（迁移可行性结论）** | 计A / 生C | 9.12 | 🔴 已出结论但被撤回 | [`transferability_D2_0912.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/transferability_D2_0912.md) + `scatter_D2_0912.png` 已产出。全表 ρ=0.3308/0.3808 可复现，但 260 行仅含 **8 条唯一 seq30**，去重后 ρ=-0.2381 (p=0.57) / -0.0952 (p=0.82)，原「≥0.30 达标、无需混合预案」判定不成立，报告已加「〇、9.13 更正补记」。 |
| `efficiency_norm` 列口径 | 生A / 计A | 9.11 | ✅ 已坐实（9.16） | 实证确认 `efficiency_norm = indel_pct × 100`（scores_merged_0911 中 260/260 行逐值相等），**并非** `04_spearman_D2.py` 注释要求的批次内百分位；全量重跑即按此实证约定重建标签，CHANGELOG「未冻结项」存疑口径就此坐实。 |

---

### 阶段 2：Stacking 模型构建 + 评估（9.13 – 9.19 · 计划工时 21h）
**目标**：提取序列与模型特征，组装元模型，按基因防泄漏分组调参，出具 LOGO-CV 与对比表。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 特征矩阵组装 | 计A | 9.14 | ✅ 已产出（9.16 重建） | 旧产物 `feature_matrix_0913.csv` / `feature_matrix_0914.csv`（260 行 × 27 列，入模 9 维）；全量版 `results/feature_matrix_full_0916.csv`（487 × 28，`scripts/13_features_train_full.py`）。 |
| 按基因防泄漏分组训练岭回归 | 计A | 9.17 | ✅ 已重跑 / ❌ 未达标但显著改善 | 旧 `meta_model_ridge_0919.joblib`（测试集 ρ=-0.3435）已弃用；全量版 [`results/meta_model_ridge_full_0916.joblib`](file:///d:/lifesciencechallenge/cs_pipeline/results/meta_model_ridge_full_0916.joblib)（alpha=316.23，solver=svd）为现行模型。LG01.6995/6999 同源合并分组、无泄漏断言通过；**LOGO-CV 中位 ρ=0.414，仍低于 ρ≥0.5 达标线**。 |
| 模型交接接口 F4（`predict.py`） | 计A $\rightarrow$ 计B | 9.17 晚 | 🟡 部分修复（9.16） | [`predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) 默认模型已切到 `meta_model_ridge_full_0916.joblib`（特征接口 9 维一致）。运行时 `crispron_score` 仍为近似公式（`deep×0.95+(tm-50)×0.25`，第 79 行），但模块 docstring 已显著标注；批量精确打分走 `demo/rescore_demo_full_0916.py`（真实 CRISPRon 经 WSL）。彻底修复（运行时真调 WSL 或移除该特征重训）仍挂 P0。 |
| 留一基因交叉验证（LOGO-CV） | 计A | 9.16 | ✅ 已重建，多数折有效 | 旧 `logo_cv_0916.csv` 7 折仅 2 折可算（中位 -0.2254）；全量版 [`results/logo_cv_full_0916.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/logo_cv_full_0916.csv) + `logo_cv_box_full_0916.png`：13 折中 7 折可定义（LG07.3296 0.68、LG02.4013 0.65、LG07.3933 0.42、LG02.4820 0.41、LG01.8265 0.22、LG01.6995/6999 0.08、LG01.555 -0.32），中位 **0.414**；6 折因留出基因仅 1 条 guide 无法定义。 |
| 模型对比表（单模型 vs 集成 $\rho$/AUC） | 计A | 9.19 | ❌ 未达标（改善后仍差 0.086） | `results/model_comparison_full_0916.csv`：LOGO-CV 中位 ρ 0.414（旧版 -0.2254）；外层测试折 ρ=-0.676 / AUC=0.074（仅 3 个留出基因且含开关式标签，单折噪声极大，不作结论依据）。$\rho \ge 0.5$ 未达，公开数据加权混合预案仍是必选项。 |
| 模型卡（Model Card）归档 | 计A $\rightarrow$ 生D | 9.19 晚 | ✅ 已补（9.16） | 接口 F5 [`results/model_card_full_0916.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/model_card_full_0916.md) 已交付：9 维特征顺序、训练集版本（487 行 / 23 条 guide）、真实 ρ/AUC、已知局限（含系数为负、内含子靶点误判、跨物种外推警告）全部如实记录；同时满足赛事附件 5 对 Model Card 的要求（适用范围、输入输出、已知局限）。 |

---

### 阶段 3：莴苣工具化 + Streamlit Demo（9.20 – 9.26 · 计划工时 21h）
**目标**：下载莴苣 T2T 基因组，全外显子/启动子候选扫描，Cas-OFFinder 离线脱靶过滤，Streamlit 交互界面交付。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 莴苣 T2T 基因组与 GFF3 索引 | 生B $\rightarrow$ 计B | 9.21 晚 | ✅ 已完成 | 存放于本地 `cs_pipeline/data/lettuce/`（大文件按规范不进 git）。 |
| 着丝粒坐标 + NLR 基因清单 | 生B $\rightarrow$ 计B | 9.23 晚 | ✅ 已完成 | 回填 661 个 de novo NLR 基因坐标，选定 49 个代表基因（[`cs_pipeline/data/demo/demo_nlr50_genes.txt`](file:///d:/lifesciencechallenge/cs_pipeline/data/demo/demo_nlr50_genes.txt)）。 |
| 莴苣全基因组 gRNA 扫描（脚本 07） | 计B | 9.23 | ✅ 已完成 | [`cs_pipeline/scripts/07_scan_lettuce.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/07_scan_lettuce.py) 完成，45,770 个基因扫描出 13,867,270 条候选，耗时 320 秒（详见 [`cs_pipeline/results/scan_stats_0923.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/scan_stats_0923.md)）。 |
| Cas-OFFinder 脱靶位点分析（脚本 08/09） | 计B | 9.24 | ✅ 已完成 | 对 demo 范围 19,839 条 gRNA 运行脱靶（GPU 分批），检出 6,088,827 个位点，汇总生成 [`cs_pipeline/results/offtarget_counts_0924.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_counts_0924.csv)。 |
| Streamlit Demo 界面开发 | 计B | 9.25 | ✅ 已完成（9.16 换血） | [`cs_pipeline/app/app.py`](file:///d:/lifesciencechallenge/cs_pipeline/app/app.py) 交付。Tab1 基因检索（4ms）与 Tab2 实时子进程打分（DeepSpCas9 24.1s）。9.16：`demo/rescore_demo_full_0916.py` 对 19,839 条候选用**真实** DeepSpCas9 + **真实** CRISPRon（WSL）+ 全量模型重打分，新列 `efficiency_score_full_0916` 写回 `demo/app_data.csv`（改前已备份）；app 优先展示新列并附「模型未达标（LOGO-CV ρ=0.414）」免责说明，旧 `efficiency_score` 列仅留档。 |
| Demo 走查与截图留痕 | 计B | 9.26 | ✅ 已完成 | 3 个真实基因端到端走查，7 张真实无敏感信息截图已落盘于 [`cs_pipeline/results/demo_screenshots_0926/`](file:///d:/lifesciencechallenge/cs_pipeline/results/demo_screenshots_0926/)。 |

---

### 阶段 4：交付冲刺（9.27 – 10.4 · 计划工时 24h）
**目标**：指标冻结、代码清理脱敏、报告/PPT/视频制作、匿名化合规审核、最终提交。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| **指标冻结与代码打 Tag** | 生D / 计B | 9.27 🔶 | ⚠️ 已冻结并两次更正 | [`CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md) 冻结了扫描与脱靶数字（可信）；9.13 更正了与磁盘产物不符的模型指标（原 ρ=0.3665 / AUC=0.7812 / p=1.10e-9 系错误记录）；9.16 增补数据更正 + 全量重跑 + demo 重打分记录。tag `v1.1-freeze` 已打；`v1.0-freeze` 本地仍缺失（需补打或删除该条声明）。 |
| 源码整理与运行说明 | 计B | 10.2 | ✅ 已提前就绪 | [`cs_pipeline/README.md`](file:///d:/lifesciencechallenge/cs_pipeline/README.md)、[`requirements.txt`](file:///d:/lifesciencechallenge/cs_pipeline/requirements.txt) 已重写并通过干净环境验证。 |
| **匿名化专项检查（红线）** | 全员 / 计B | 10.3 🔶 | ✅ CS侧已提前通关 | 详见 [`cs_pipeline/docs/reports/anonymization_checklist_1003.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/reports/anonymization_checklist_1003.md)，代码、注释、提交者（`team`）、截图路径等全部零命中。 |
| 评审表/报告书主稿 | 生D 主笔 / 全员 | 9.28–10.1 | ⏸ 待开启/网盘进行 | 代码库中暂无 Word/PDF 主件（按规范存于团队共享网盘 `LSC_共享/deliverables/`）。赛事三个附件（附件 2/3/5 定稿）已归档至 `docs/notification/`；附件 5 要求的 Model Card 已由 `results/model_card_full_0916.md` 覆盖（适用范围、输入输出、已知局限三要素齐全）。 |
| PPT 制作 + 录音台词 | 生D / 全员 | 9.30 | ⏸ 待开启/网盘进行 | 同上。 |
| 演示视频录制 | 生D / 计B | 10.1 | ⏸ 待录制 | 计B 已提供 7 张截图与走查路线，录屏待生物系/PM 统筹执行。 |
| **最终材料提交（硬截止）** | 生D | 10.4 | ⏸ 待提交 | 距离截止仍有充足时间。 |

---

## 三、跨组接口交接履约审计表（F1 – F7）

对照《分工详案_总控》（docs/plans/division_plan_master.md）第二节定义的 7 个关键交接接口：

| 接口 | 交付方 $\rightarrow$ 接收方 | 交付内容 | 计划死线 | 当前履约情况 |
|:---:|:---:|---|:---:|---|
| **F1** | 生A $\rightarrow$ 计A | Hi-TOM 清洗表（12 列标准） | 9.9 晚 | ✅ **已履约**：`data/hitom/hitom_clean_v1.csv` + `hitom_seq30_0909.csv` 已入库；9.16 全量重建版 `hitom_clean_full_0916.csv` / `hitom_seq30_full_0916.csv`（487 行）为现行事实源。 |
| **F2** | 生B $\rightarrow$ 计B | 莴苣 T2T 基因组 + 注释 GFF3 | 9.21 晚 | ✅ **已履约**：基因组已索引，全基因组外显子/启动子扫描已闭环。 |
| **F3** | 生B $\rightarrow$ 计B | 着丝粒坐标 + NLR 基因清单 | 9.23 晚 | ✅ **已履约**：回填完成，生成 demo 专用的 49 个 NLR 基因表。 |
| **F4** | 计A $\rightarrow$ 计B | 模型预测接口（`predict.py` + 模型权重） | 9.17 晚 | 🟡 **部分修复（9.16）**：`predict.py` 默认模型已切全量版 `meta_model_ridge_full_0916.joblib`（LOGO-CV ρ=0.414，仍未达标）；demo 批量供分已改走真实双模型管线（`rescore_demo_full_0916.py`），修复了旧接口的 CRISPRon 特征伪造问题。残留：`predict.py` 运行时 `crispron_score` 仍为近似公式（docstring 已显著标注），彻底修复挂 P0。 |
| **F5** | 计A $\rightarrow$ 生D | 模型卡（`model_card.md`） | 9.19 晚 | ✅ **已履约（9.16）**：`results/model_card_full_0916.md` 已归档，真实 ρ/AUC、9 维特征顺序、有效样本量（23 条 distinct guide）与已知局限全部如实记录；旧 0919 模型的模型卡标注为从未交付且模型弃用。 |
| **F6** | 计B $\rightarrow$ 生C | 候选 gRNA 结果表（供生物学核查） | 9.24 晚 | ✅ **已履约**：19,839 条 demo 候选表已合成，脱靶与着丝粒标注齐全；9.16 追加 `efficiency_score_full_0916` 真实重打分列。 |
| **F7** | 全员 $\rightarrow$ 生D | 报告、PPT 与申报素材集中汇总 | 9.28 齐 | 🟡 **部分就绪**：CS 侧工具链素材、扫描脱靶数据、Demo 截图、模型卡已备齐；模型指标（LOGO-CV 0.414，未达标）的答辩口径与生物学文案待齐。 |

---

## 四、当前可直接运行与验收的交付物清单

如果评审专家或团队负责人现在检查代码仓库，**以下成果可以直接运行验证**：

1. **Streamlit 演示 Demo（Tab1 检索 + Tab2 实时打分）**
   - 启动命令：
     ```bash
     cd cs_pipeline
     conda run -n grna-demo streamlit run app/app.py
     ```
   - 可验证内容：
     - 输入 NLR 基因（如 `LsaT2T01G023690`）立即展示 300+ 条候选 gRNA 及其脱靶数、着丝粒过滤状态；
     - Tab1 的「效率分」列现为 `efficiency_score_full_0916`（9.16 用**真实** DeepSpCas9 + **真实** CRISPRon + 全量模型重打分），界面附「模型未达标（LOGO-CV ρ=0.414），仅供流程演示」的免责说明；旧 `efficiency_score` 列（旧模型 + 近似 CRISPRon 特征）仅留档不再展示；
     - 切换到 Tab2，输入两条 30bp 序列，子进程调用 DeepSpCas9 实测打分（返回 71.25 / 46.28），DeepSpCas9 分为真实推理可正常演示。
2. **基因组与脱靶全流程处理脚本**
   - [`cs_pipeline/scripts/07_scan_lettuce.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/07_scan_lettuce.py)：已验证可 320 秒扫完整基因组；
   - [`cs_pipeline/scripts/09_aggregate_offtarget.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/09_aggregate_offtarget.py)：已验证可聚合 600 万条脱靶原始记录；
   - [`cs_pipeline/demo/prepare_demo_data.py`](file:///d:/lifesciencechallenge/cs_pipeline/demo/prepare_demo_data.py)：已验证可自动装配 demo 所需数据。
3. **全量训练管线（9.16 重建，scripts/10~13）**
   - `10_rebuild_full_dataset.py`（xlsx→clean→seq30，487/487 全命中）→ `11_score_deepspcas9_full.py` → `12_score_crispron_full.py`（WSL）→ `13_features_train_full.py`（特征+训练+LOGO-CV）；
   - 以改正版 `data/1_Hi-results-12-20260913.xlsx` 为唯一事实源，全程防泄漏断言通过。
4. **已落盘的冻结/现行成果文件**
   - 扫描统计：[`cs_pipeline/results/scan_stats_0923.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/scan_stats_0923.md)
   - 脱靶日志：[`cs_pipeline/results/offtarget_runlog_0924.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_runlog_0924.md)
   - 脱靶计数：[`cs_pipeline/results/offtarget_counts_0924.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_counts_0924.csv)
   - Demo 运行截图 7 张：[`cs_pipeline/results/demo_screenshots_0926/`](file:///d:/lifesciencechallenge/cs_pipeline/results/demo_screenshots_0926/)
   - 现行模型与指标：`results/meta_model_ridge_full_0916.joblib`、`model_comparison_full_0916.csv`、`logo_cv_full_0916.csv`、`logo_cv_box_full_0916.png`
   - 模型卡（F5）：[`results/model_card_full_0916.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/model_card_full_0916.md)

---

## 五、下一步行动路线图（9.17 复核后重订）

9.13 路线图提出的「有效样本量」卡点已被 9.14–9.16 的数据更正部分消解（8 条唯一 guide → 23 条 distinct guide / 487 行，LOGO-CV -0.225 → +0.414）。**当前卡点已收敛为一个：guide 多样性不足**。

```
              【当前真实卡点：guide 多样性】

487 行 / 14 基因 / 23 条 distinct guide
        │
        ├─ 8 个基因只有 1 条 guide ──→ 特征全部由序列派生，
        │     单 guide 基因内所有行特征向量相同，
        │     LOGO 6 折无法定义 ρ；ρ≥0.5 结构性不可达
        │
        ▼
结论：再堆同一 guide 的重复行不会提升
      唯一出路 = 详案规定的「公开数据加权混合」预案（Table S1）
```

### 1. 计A 必做项（按优先级）
- **P0 启动公开数据混合预案**（9.13 起挂账，仍未启动）：下载 DeepSpCas9 Table S1 入库 `data/deepspcas9_tableS1.xlsx`（详案规定的唯一扩充途径），与自有 487 行数据加权混合后重训（在 `scripts/13` 基础上改），重新出具 LOGO-CV ρ；若达标则同步更新模型卡与 demo 供分。
- **P0（残留）修 `predict.py` 运行时 CRISPRon 特征**：第 79 行近似公式改为经 WSL 真实调用 CRISPRon（`env/run_crispron_wsl.sh` 已可用且路径已修），或从 9 维特征集中移除 `crispron_score` 后重训；当前状态（近似公式 + docstring 显著标注 + 批量走真实管线）只是过渡，正式提交前须闭环。
- **P1 提交 9.14–9.16 工作成果**：数据更正脚本（仓库根 `_check_*` / `_fix_*`）、更正版 xlsx 备份链、`scripts/10~13` 与 `_full_0916` 产物目前大量处于未提交/未跟踪状态，需整理入库（数据更正的溯源链是答辩材料的一部分）。
- ~~P1 评估口径纠正~~：**已完成（9.16）**——主指标已改用 LOGO-CV，按基因分组防泄漏（同源拷贝合并分组），输出含可定义折数说明，260 行虚假显著性问题不再存在。
- ~~P1 补 F5 模型卡~~：**已完成（9.16）**——`results/model_card_full_0916.md`。
- ~~P2 核对 `efficiency_norm`~~：**已坐实（9.16）**——该列 = `indel_pct × 100`，非批次内百分位，全量重跑按实证约定重建标签。

### 2. 计B / 生D 协同项
- ~~计B：demo 效率分降级/免责~~：**已完成（9.16）**——`app/app.py` 优先展示 `efficiency_score_full_0916` 并附「模型未达标（LOGO-CV ρ=0.414）」说明，旧列仅留档。
- **生D（PM）**：`CHANGELOG_0927.md` 的 9.13 与 9.16 两段更正记录需全队过一遍并会签；补打缺失的 `v1.0-freeze` tag（或删除该条声明）；评审表与 PPT 中**不得引用 ρ=0.3665 / AUC=0.7812 / p=1.10e-9 这组已被更正的数字**；可引用 LOGO-CV 中位 ρ=0.414，但须同时注明未达 ρ≥0.5 达标线与 guide 多样性瓶颈；若混合预案后仍未达标，答辩口径应转为「工程链路完整 + 数据规模受限的诚实说明」，而非硬报达标。
- **生A / 生C**：47 条未命中 CDS 的 guide 核对已被全量重跑取代（487/487 全命中，72 行走基因组坐标回退，自校验断言通过），无需再单独核对；可顺手确认 Hi-TOM 原始交付是否还有未纳入本仓库的其他 guide 序列（每多一条不同序列的 guide 都比重复行有价值）；oligo 合成记录若能拿到仍建议留存（9.16 已按现有证据链定稿，不阻塞）。

---

## 六、9.18–9.21 进展纪事与现行口径（9.21 更新）

> 本节为现行事实源。第一至五节中所有 487 行 / ρ=0.414 / 23 条 guide 的表述均为 0916 旧口径，保留存档不再逐处修订。

### 6.1 数据基线：487 行 → 1368 行（24 批次）

- 9.18：NEWdata 17 批次 877 行整理并入主表 → `data/1_Hi-results-13-merged-20260918.xlsx`（1368 行 / 24 批次 / 14 列；过程文档 `docs/problem3.md`）。可打分 1361 行（`data/hitom/hitom_seq30_merged_0918.csv`）；7 行无模型分（4 行非 NGG-ACT + 3 行 USR-6137 无 seq-20）
- 9.21：`NEWdata/` 目录撤销——经 MD5 全量核对，唯一文件并入 `data/raw/hitom/NEWdata_0918/`（18 个批次 xls + 138 个唯一 fastq（USR-23709 原始 reads 唯一拷贝）+ 5 个旧批次唯一 xls），纯冗余删除（138 个备份 fastq + 4 个重复 xls）；归并记录见该目录 README
- 数据版本链：12（0913，487 行旧口径源）→ 13-merged（0918，1368）→ 14-scoring（0920，A/B/D 分级）→ 15-efficiency（0920，+4 列效率分）→ 16（0921，裁决修正）→ **16.1（0921，现行交付版）**

### 6.2 9.19 老师裁决（现行剔除口径）

- 唯一裁决源：`results/excluded_gids_final_0919.csv`（360 行 = QC 口径 253 + USR-14333 整批 87「疑 T2 代测序」+ USR-22807 整批 20「参照与基因型不配套」）；USR-5448（杂合子材料）/ USR-6137 QC 撤销恢复保留
- ⚠️ 裁决无原始凭证文件：同学回传的"(4).xlsx"经 md5 验证只是 13-merged 的重复下载副本（无任何批注）；计B批注版的裁决回写也不完整（14333/22807 仅 73/107 行带标签，5448/6137 QC 撤销 0 行回写）——这正是 15 版 B2 脱节的根源。**建议向老师补要书面裁决记录**
- 9.19 锚定重跑（1005 行）：raw LOGO-CV 中位 ρ=-0.2623 → 批次偏移锚定后 -0.0785（`b_anchor_final_0919.csv`）；中间版裁决（941 行）锚定曾得 +0.1542（`b_anchor_postruling_0919.csv`）；6137 无 WT 行单列核查为 -0.15 危害源

### 6.3 16.1 版交付口径（9.21，现行）

`data/1_Hi-results-16.1-efficiency-20260921.xlsx`：**1368 = 训练集 969 + 保留-不可打分 3 + 剔除(9.19裁决) 360 + 剔除(弱信号,待老师追认) 36**；969 + 36 = 1005 与裁决保留的可打分行数精确闭环。

- 分级：A 906 / B 91 / D 368 / 待定 3（不可打分行）；等级只表征 guide 身份证据强度，剔除以处理状态列为准
- 效率分（B1 修复口径）：综合分 = 两模型组内纯百分位均值×100（并列同值），排名并列同名次；969 行仅 36 个 distinct 分数对 → 32 个名次档，最大并列组 239 行同分同名次（15 版曾被人为摊到 25.7 分跨度，已消除）
- r(综合分, indel_pct) = 0.044 (Pearson) / 0.111 (Spearman)，n=969——模型分只作排序/择优，不作实测替代
- 审计链：`results/b_audit_0919.md`（QC 复核 / 更正落地 / 敏感性）→ `results/b_audit_0920.md`（15 版 B1 抖动 + B2 裁决脱节 + G 回传文件交叉核对）；修复与核对脚本 `scripts/dev/b_fix_16_postruling_0921.py` / `b_fix_161_pending_grades_0921.py` / `b_crosscheck_0921.py`（全部可复现，断言自检通过）
- guide候选表（61 条 / 35 ref，在 `1_Hi-results-13-merged-20260918_计B批注版.xlsx`）已回传：15 版 219 行非剔除"待设计表确认"分级复推 **219/219 一致**、判定依据引用热点分数 0 不符；22 行"待定"补定级（16 行 refM Top1=68077→A/80；6 行 refSP1 Top1=62→弱信号 D/25）；生物负责人检查清单（`docs/reports/bio_lead_checklist_0920.md`）第一节自此可执行

### 6.4 现行模型指标一览（诚实口径）

| 口径 | n 行 | LOGO-CV 中位 ρ | 备注 |
|---|---|---|---|
| 0916 full（旧，第二节引用源） | 487 | **0.414** | 对 indel=1 行极敏感：去掉 101 行 → 0.596；去掉 USR-8145 → 0.477（`b_sensitivity_logo_0919.csv`） |
| 0918 merged 全表 | 813 | -0.257 | 未剔 QC，噪声主导（`logo_cv_merged_0918.csv`） |
| 0918 confident | 544 | 0.247 | （`logo_cv_confident_0918.csv`） |
| 0919 裁决后 raw | 1005 | -0.262 | `b_anchor_final_0919.csv` |
| 0919 裁决后 anchor | 1005 | -0.079 | 批次偏移锚定 |
| **0921 复跑 ruling1005** | 1005 | raw -0.220 / anchor **-0.078** | `b_anchor_161_0921.py` 代码路径同 0919，复现于浮点噪声级（13/18 折） |
| **0921 train969（16.1 训练集）** | 969 | raw -0.248 / anchor **+0.310** | 剔弱信号 36 行后锚定口径 -0.08→+0.31，**弱信号剔除的实证支持**（12/17 折，`b_anchor_161_0921.csv`） |
| 0921 noB879（去 B 级 90 行） | 879 | raw +0.366 / anchor +0.297 | 有效折掉到 9~10/16，中位数与上两行可比性弱；锚定口径下 B 级影响小（0.310→0.297），与"预期很小"一致 |

**结论：ρ≥0.5 在所有口径下均未达标**，现行最好数字 = train969 锚定 **+0.310**。0.414 是旧 487 行小基线数字且依赖 indel=1 行；扩表 + 裁决后一度回落至 ~0，剔弱信号后部分回升。结构性瓶颈未变且被扩表进一步坐实：969 行训练集只有 36 个 distinct 模型分数对（同 guide 跨块复用），基因内排序信号稀薄。

### 6.5 当前待办（9.21 时点）

1. ~~以 16.1 口径重跑锚定 + LOGO~~ **已完成（9.21）**：`scripts/dev/b_anchor_161_0921.py` → `results/b_anchor_161_0921.csv`（ruling1005 复现 / train969 / noB879 三人群 × raw/anchor，见 6.4 表）
2. **P0 弱信号 36 行交老师追认**——现已带实证：剔除后锚定 LOGO 由 -0.078 升至 **+0.310**（弱信号行 seq-20 身份不明，属特征噪声源）；同时补要 9.19 裁决书面记录
3. **P0 公开数据混合预案仍未启动**（第五节 P0 沿用：DeepSpCas9 Table S1 加权混合是达标的唯一未尝试途径）
4. P1 双 gRNA 块 63 行 -A/-B 拆分（不需台账，切点反推可执行；拆分前训练建议降权）
5. P1 生物负责人检查清单现在可发出执行（guide候选表已就位）；mR1 编号含义（2 行）待生物侧说明
6. P1 `predict.py` 运行时 CRISPRon 近似公式闭环（第五节 P0 残留，正式提交前必须处理）

