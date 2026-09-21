# 菊科菊苣族 gRNA 设计工具项目进展全景审计报告

> **依据文档**：
> - [`docs/plans/project_plan_v3_condensed_0907.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/project_plan_v3_condensed_0907.md)（主方案）
> - [`docs/plans/division_plan_master.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_master.md)（甘特图与接口规范）
> - [`docs/plans/division_plan_cs.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_cs.md)（技术实施标准）
> - [`docs/problem.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem.md) / [`docs/problem2.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem2.md) / [`docs/problem3.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/problem3.md)（9.14–9.16 数据更正、9.18 扩表并入全过程）
> - [`results/CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md)（冻结记录，含 9.13 / 9.16 两段更正；**9.18–9.21 段待补**）
> - [`results/b_audit_0919.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/b_audit_0919.md) / [`results/b_audit_0920.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/b_audit_0920.md)（两轮独立审计）
> - [`docs/reports/scoring_rules_14-15_0920.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/reports/scoring_rules_14-15_0920.md) / [`docs/reports/scoring_rules_16_post_ruling_0921.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/reports/scoring_rules_16_post_ruling_0921.md)（打分版规则与 16/16.1 修正说明）
> - [`results/model_card_full_0916.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/model_card_full_0916.md)（模型卡，**0916/487 行冻结口径；随生产模型口径决策重写或补注**）
> - 计算机系流水线全量代码与产物目录：[`cs_pipeline/`](file:///d:/lifesciencechallenge/cs_pipeline/)
>
> **审计基准时点**：2026-09-21 复核（最新 commit `cc47cd0`；9.18 扩表 1368 行、9.19 老师裁决落地、9.20–9.21 打分版 14/15/16/16.1 交付链与两轮独立审计、16.1 口径 LOGO 重跑全部完成）
>
> **📌 9.21 更新要点**（9.17 版要点见 git 历史 `590bff6` 前版本）：
> ① **数据层已闭环**：基线 487 行 → 1368 行 / 24 批次（9.18 NEWdata 877 行并入，9.21 NEWdata 目录经 MD5 核验并入 `data/raw/hitom/NEWdata_0918/` 后撤销）；9.19 老师裁决（剔 360 行）已落地为唯一剔除口径；现行交付版 **16.1**：1368 = 训练集 969 + 不可打分 3 + 裁决剔除 360 + 弱信号待追认 36（969+36=1005 与锚定口径闭环）。
> ② **模型层仍未达标，且"达标出路"已穷尽**：16.1 口径重跑（`b_anchor_161_0921.csv`）现行数据口径最好数字 = train969 锚定 LOGO-CV 中位 ρ=**+0.310**（12/17 折），低于 ρ≥0.5 达标线；ρ=0.414 是 **v2.0 冻结生产模型**（full_0916，487 行裁决前口径）的官方冻结数字，引用时必须限定口径，不得当作现行数据口径指标（其对 indel=1 行高度敏感：去掉即 0.596，见 `b_sensitivity_logo_0919.csv`）。剔弱信号 36 行使锚定 LOGO 由 -0.078 → +0.310，为弱信号剔除提供了实证。**更正**：公开数据混合预案并非"未启动"——9.17 已执行两轮（人源 Luo2020_Kim2019 23,902 条 + 番茄 Cucuy 420 条），结论均"无害但无增量"，公开渠道穷尽、建模按详案纪律两次终结（CHANGELOG 9.17 各条）；本报告前一版沿用了旧第五节的过期表述，现已修正。
> ③ **15 版经独立审计发现并修复两个阻断问题**（效率分 tie-break 抖动、9.19 裁决未落地，`b_audit_0920.md`）；guide候选表（61 条）已回传并 100% 复推验证 15 版 219 行分级；"(4).xlsx"证实为重复下载副本——**9.19 裁决无原始凭证文件**，需补要书面记录。
> ④ **模型权重/模型卡/demo 供分仍是 v2.0 冻结的 0916 口径**（487 行、ρ=0.414 免责文案），与现行数据口径（16.1/969 行、+0.310）脱节；是否按 16.1 口径重训替换冻结模型，按 CHANGELOG 冻结规则**须全队讨论会签**（CHANGELOG 9.21 条第 8 款已登记决策点）。

---

## 一、执行摘要：我们在哪里？

数据治理链路（扩表 → 裁决 → 分级 → 审计 → 修正）已在 9.21 闭环到 16.1 版，训练集口径与老师裁决精确对齐；工程链路（计B）维持 10.3 交付状态、指标可信；算法链路（计A）在扩表后一度回落、剔弱信号后部分回升（锚定 LOGO +0.310），**仍未达 ρ≥0.5 达标线**，且模型权重、模型卡、demo 供分尚停留在 0916/487 行旧口径。结构性瓶颈依旧是 **guide 多样性**：969 行训练集只有 35 条 distinct guide（最大并列组 239 行同一 guide），扩表 877 行仅贡献 12 条新序列——堆重复行无效的结论被进一步坐实。

```mermaid
graph TD
    classDef done fill:#d4edda,stroke:#28a745,color:#155724;
    classDef bad fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef pend fill:#fff3cd,stroke:#ffc107,color:#856404;

    A[阶段0: 数据清洗与环境搭建]:::done --> B[阶段1: 预训练模型打分与D2可行性]:::bad
    B --> C[阶段2: Stacking岭回归训练与评估]:::pend
    C -->|F4 predict.py 仍挂0916旧模型| D[阶段3: 莴苣工具化与Streamlit Demo]:::done
    D --> E[阶段4: 成果冻结与交付冲刺]:::pend

    subgraph 计B负责: 已闭环且指标可信
        D
        F[全外显子/启动子扫描 13.87M]:::done
        G[Cas-OFFinder 脱靶 6.08M]:::done
        H[Streamlit 双Tab交互与截图]:::done
        I[10.3 匿名化检查与代码打包]:::done
    end

    subgraph 数据治理 9.18-9.21: 已闭环
        M[扩表1368行/24批次 → 16.1版训练集969]:::done
        N[9.19裁决落地 + 两轮独立审计 + guide候选表验证]:::done
    end

    subgraph 计A负责: 改善但未达标 🟡
        B
        C
        J[16.1口径重跑: 锚定LOGO +0.310 未达标]:::pend
        K[D2 迁移 ρ: 去重后为负且不显著, 已撤回]:::bad
        L[模型权重/模型卡/demo供分仍是0916旧口径]:::bad
    end
```

### 核心结论速览
1. **数据治理（生A/计B 协同，9.18–9.21）已闭环，口径可信**：
   - 1368 行 / 24 批次主表（`1_Hi-results-13-merged-20260918.xlsx`）为表级基线；9.19 老师裁决（`excluded_gids_final_0919.csv`，360 行）为唯一剔除口径；
   - 现行交付版 **`data/1_Hi-results-16.1-efficiency-20260921.xlsx`**：训练集 969 + 不可打分 3 + 裁决剔除 360 + 弱信号待追认 36；A/B/D 证据分级 + 效率综合分（纯百分位、并列同名次）；
   - 两轮独立审计（`b_audit_0919.md` / `b_audit_0920.md`）+ 修复脚本链（`b_fix_16` / `b_fix_161` / `b_crosscheck_0921`）全部可复现；guide候选表 61 条对 15 版 219 行分级复推 100% 一致。
2. **计A（算法模型链条）现状：改善但未达标，且产物口径滞后**：
   - 16.1 口径重跑（`b_anchor_161_0921.csv`）：ruling1005 复现 0919 结果（锚定 -0.078）；**train969 锚定 LOGO-CV 中位 ρ=+0.310（现行最好，12/17 折）**；去 B 级 879 行对锚定口径影响小（+0.297）；
   - 剔弱信号 36 行使锚定 LOGO -0.078 → +0.310：身份不明 guide 的 seq-20 属特征噪声源，此为弱信号剔除的实证支持（待老师追认）；
   - **仍未达 ρ≥0.5**；ρ=0.414 为 v2.0 冻结生产模型（487 行裁决前口径）官方数字，引用须限定口径；+0.310 为现行 16.1 数据口径评估值——对外采用哪个口径按冻结规则由全队会签（CHANGELOG 9.21 条第 8 款）；
   - ⚠️ 现行落盘权重 `meta_model_ridge_full_0916.joblib`、模型卡、demo 供分列均为 487 行旧口径；**是否按 16.1 基线重训替换冻结模型是团队决策点**（重训技术上随时可做，评估框架 `b_anchor_161_0921.py` 现成），决策后联动模型卡重写、F4/demo 换权重与免责文案更新；
   - 瓶颈定性（更新）：969 行 / 17 基因组 / **35 条 distinct guide**，5 个基因仅 1 条 guide（LOGO 5 折无法定义）；**公开数据混合预案 9.17 已两轮执行终结（人源 + 番茄，均"无害但无增量"），同物种/同科检索穷尽（自有 23 条 guide 已是该物种最大 per-guide 效率集）——不存在可操作的达标出路**，答辩叙事按 CHANGELOG 9.17 定调：迁移衰减三段对照（本氏烟成功/番茄失效/橡胶草部分）+ 工程链路完整 + 数据规模受限的诚实说明。
3. **计B（工程与工具链）维持 10.3 交付状态，指标可信**：
   - 莴苣 T2T 全基因组 45,770 基因扫描（13,867,270 条候选）、Cas-OFFinder 脱靶（19,839 条 demo gRNA / 608 万位点）、Streamlit demo、7 张截图、匿名化零命中，全部就绪且已冻结；
   - ⚠️ 唯一滞后点：demo 免责文案仍引用「LOGO-CV ρ=0.414」且未注明数据口径，须随生产模型口径决策同步更新。

---

## 二、全员里程碑与甘特表逐项对比（阶段 0 – 阶段 4）

### 阶段 0：数据盘点 + 环境准备（9.7 – 9.9 · 计划工时 9h）
**目标**：Hi-TOM 数据清洗定档 D1，conda 环境装配，验证预训练单序列打分。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| Hi-TOM 原始数据清洗与 12 列规范 | 生A | 9.8 晚 | ✅ 已完成（9.18 扩表、9.21 归并） | 初版 `hitom_clean_v1.csv`（307 行）→ 9.16 全量 487 行 → **9.18 并入 NEWdata 877 行成 1368 行 / 24 批次主表**，现行模型输入 `data/hitom/hitom_seq30_merged_0918.csv`（1361 行可打分）。9.21：NEWdata 目录经 MD5 全量核验并入 `data/raw/hitom/NEWdata_0918/`（唯一 fastq 138 个保留，冗余删除）后撤销。 |
| **数据表系统性检查与更正（9.14 起专项）** | 计A / 计B | — | ✅ 已完成（链条延续到 9.21） | 9.14–9.16 更正（strand 221 行、5712 序列+indel 口径 61 行、6995/6999 移位 32 行、PAM CCA→ACT 4 行等，`problem.md`/`problem2.md`）；9.18 扩表并入（`problem3.md`）；9.20 同学 14/15 版分级打分；**9.21 独立审计发现 15 版两个阻断问题并修复为 16/16.1 版**（`b_audit_0920.md`，含 9.19 裁决落地与效率分去抖动）。溯源链完整：每步有备份、脚本、审计文档。 |
| 补齐 30bp 上下文序列 | 计A | 9.9 晚 | ✅ 已完成（9.18 全量重建） | 现行 `hitom_seq30_merged_0918.csv`（1361 行）；旧产物 `hitom_seq30_full_0916.csv`（487 行）留档。7 行无 seq-20/非 NGG 无模型分，已单列"保留(不可打分,待复核)"。 |
| conda 主环境与 demo 环境搭建 | 计A / 计B | 9.9 晚 | ✅ 已完成 | `crispr`（py3.10+genet+TF2.9）与 `grna-demo` 环境已分离；CRISPRon Windows 原生与 WSL 路线均通；scipy 1.14.1 降级根治 cholesky 崩溃。 |
| 示例序列打分验证 | 计A | 9.9 晚 | ✅ 已完成 | DeepSpCas9 71.2494（基准 71.25）；CRISPRon 341 条官方测试逐字节一致。 |
| **决策点 D1（路线定档）** | 全员 | 9.8 晚 | ✅ 已定案 | 纯 Stacking 路线。9.18 扩表后数据规模问题已解（1368 行），**卡点转移为 guide 多样性**（见第五节）。 |

---

### 阶段 1：预训练模型批量打分 + 迁移可行性 D2（9.10 – 9.12 · 计划工时 9h）
**目标**：用两个预训练模型给自有橡胶草数据打分，评估其在植物上的迁移相关系数（Spearman $\rho$）。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| DeepSpCas9 批量打分 | 计A | 9.10 | ✅ 现行（9.18 全量） | 现行 `results/scores_deepspcas9_merged_0918.csv`（1361 行，guide-id 与主表/hitom 同编号系）；旧版 `_full_0916`（487 行）/`_0910`（260 行）留档。 |
| CRISPRon 批量打分 | 计A | 9.11 | ✅ 现行（9.18 全量） | 现行 `results/scores_crispron_merged_0918.csv`（1361 行）。⚠️ **编号地雷（已处置）**：`scores_merged_merged_0918_DEPRECATED.csv` / `feature_matrix_merged_0918_DEPRECATED.csv`（813 行，9.21 已改名标注）使用另一套 guide-id 编号（如 TKS_0795 在两套编号下指向不同批次/序列），跨文件禁止按 guide-id join，只能按行内自带序列使用（`b_audit_0920.md` D 节、CHANGELOG 9.21 条第 6 款）。 |
| 预备公开数据集 Table S1 | 计A | 9.11 | ✅ 等价数据已入库，预案已执行并终结（9.17） | Table S1 本体未下载，但等价数据 `data/raw/public_datasets/Luo2020_Kim2019.xlsx`（23,902 条 distinct 30mer）已入库并两轮混合试验（人源 50:1~2000:1 扫描 + 番茄 Cucuy 420 条）：结论均"**无害但无增量**"；连同本氏烟迁移检验与同科/同种穷尽检索，公开渠道全部关闭（CHANGELOG 9.17 各条、`results/transferability_0917.md`）。 |
| **决策点 D2（迁移可行性结论）** | 计A / 生C | 9.12 | 🔴 已出结论但被撤回 | 260 行仅 8 条唯一 seq30，去重后 ρ=-0.2381 (p=0.57)，原「≥0.30 达标」判定不成立，报告已加更正补记。 |
| `efficiency_norm` 列口径 | 生A / 计A | 9.11 | ✅ 已坐实（9.16） | `efficiency_norm = indel_pct × 100`（260/260 逐值相等），非批次内百分位。 |

---

### 阶段 2：Stacking 模型构建 + 评估（9.13 – 9.19 · 计划工时 21h）
**目标**：提取序列与模型特征，组装元模型，按基因防泄漏分组调参，出具 LOGO-CV 与对比表。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 特征矩阵组装 | 计A | 9.14 | 🟡 现行路径已改为脚本内联 | 0916 产物 `feature_matrix_full_0916.csv`（487×28）与 `feature_matrix_merged_0918_DEPRECATED.csv`（813 行，编号地雷已标注）留档；现行评估管线 `b_anchor_final_0919.py` / `b_anchor_161_0921.py` 在脚本内从 `hitom_seq30_merged_0918.csv` 直接构建特征（gc/tm/poly_t/pam_n + 双模型分），人群按 16.1 处理状态筛选。 |
| 按基因防泄漏分组训练岭回归 | 计A | 9.17 | ⚠️ 冻结权重为旧口径，切换待全队决策 | 现行落盘权重仍为 v2.0 冻结的 `meta_model_ridge_full_0916.joblib`（487 行旧口径，LOGO 0.414）；16.1 口径 train969 锚定 LOGO=**+0.310**（12/17 折）仍未达标，评估用 Ridge 未落盘为交付权重。是否重训切换按冻结规则全队会签（第五节决策项、CHANGELOG 9.21 条第 8 款）。LG01.6995/6999 同源合并分组、无泄漏断言沿用。 |
| 模型交接接口 F4（`predict.py`） | 计A $\rightarrow$ 计B | 9.17 晚 | 🟡 双重滞后 | ① 运行时 `crispron_score` 仍为近似公式（docstring 已标注，批量走真实管线）——正式提交前必须闭环（P0）；② 默认挂载模型为 0916 冻结权重——是否切换随生产模型口径决策。 |
| 留一基因交叉验证（LOGO-CV） | 计A | 9.16 | ✅ 现行（9.21 重跑） | 现行 `results/b_anchor_161_0921.csv`：ruling1005 raw -0.220 / anchor -0.078（复现 0919）；**train969 raw -0.248 / anchor +0.310**；noB879 raw +0.366（仅 9/16 折，不可比）/ anchor +0.297。历史各口径全景见第六节 6.4 表。round(6) 常数折守卫沿用。 |
| 模型对比表（单模型 vs 集成 $\rho$/AUC） | 计A | 9.19 | ❌ 未达标（最好 +0.310 vs 线 0.5） | `model_comparison_full_0916.csv` 为旧口径；16.1 口径下单模型 vs 集成的正式对比表待重训决策后一并出具。公开数据混合预案 9.17 已两轮执行终结（无增量），不再是待选项。 |
| 模型卡（Model Card）归档 | 计A $\rightarrow$ 生D | 9.19 晚 | ⚠️ 口径待决策 | `model_card_full_0916.md` 基于 487 行 / ρ=0.414（v2.0 冻结口径）；随生产模型口径决策处理——重训则按 16.1 口径重写（真实 ρ、969/1005 行、35 条 distinct guide、已知局限），维持冻结则补注口径限定与现行评估值；两种情况均满足赛事附件 5 三要素。 |

---

### 阶段 3：莴苣工具化 + Streamlit Demo（9.20 – 9.26 · 计划工时 21h）
**目标**：下载莴苣 T2T 基因组，全外显子/启动子候选扫描，Cas-OFFinder 离线脱靶过滤，Streamlit 交互界面交付。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 莴苣 T2T 基因组与 GFF3 索引 | 生B $\rightarrow$ 计B | 9.21 晚 | ✅ 已完成 | 存放于本地 `cs_pipeline/data/lettuce/`（大文件按规范不进 git）。 |
| 着丝粒坐标 + NLR 基因清单 | 生B $\rightarrow$ 计B | 9.23 晚 | ✅ 已完成 | 回填 661 个 de novo NLR 基因坐标，选定 49 个代表基因（`data/demo/demo_nlr50_genes.txt`）。 |
| 莴苣全基因组 gRNA 扫描（脚本 07） | 计B | 9.23 | ✅ 已完成 | 45,770 基因 → 13,867,270 条候选，320 秒（`results/scan_stats_0923.md`）。 |
| Cas-OFFinder 脱靶位点分析（脚本 08/09） | 计B | 9.24 | ✅ 已完成 | 19,839 条 demo gRNA → 6,088,827 位点（`results/offtarget_counts_0924.csv`）。 |
| Streamlit Demo 界面开发 | 计B | 9.25 | ✅ 已完成（9.16 换血）⚠️ 免责文案口径待更新 | `app/app.py` 交付；Tab1 检索 + Tab2 实时打分。9.16 已用真实双模型重打分 19,839 条（`efficiency_score_full_0916`）；**界面免责文案仍引用「LOGO-CV ρ=0.414」且未注明数据口径**，供分模型为 v2.0 冻结权重——随生产模型口径决策一并处理（重训则重打分+换文案；维持冻结则文案补口径标注）。 |
| Demo 走查与截图留痕 | 计B | 9.26 | ✅ 已完成 | 3 个真实基因端到端走查，7 张截图（`results/demo_screenshots_0926/`）。 |

---

### 阶段 4：交付冲刺（9.27 – 10.4 · 计划工时 24h）
**目标**：指标冻结、代码清理脱敏、报告/PPT/视频制作、匿名化合规审核、最终提交。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| **指标冻结与代码打 Tag** | 生D / 计B | 9.27 🔶 | ⚠️ 已冻结两段，9.18–9.21 段待补 | `CHANGELOG_0927.md` 冻结扫描/脱靶数字（可信）+ 9.13/9.16 两段更正；**9.18 扩表、9.19 裁决、9.20–21 版本链 14→16.1、两轮审计、LOGO 重跑尚未写入 CHANGELOG**，需补一段并全队会签。tag `v1.1-freeze` 已打；`v1.0-freeze` 本地缺失（补打或删除声明）。 |
| 源码整理与运行说明 | 计B | 10.2 | ✅ 已提前就绪 | `cs_pipeline/README.md`、`requirements.txt` 已重写并通过干净环境验证。 |
| **匿名化专项检查（红线）** | 全员 / 计B | 10.3 🔶 | ✅ CS侧已提前通关 | `docs/reports/anonymization_checklist_1003.md`，零命中。 |
| 评审表/报告书主稿 | 生D 主笔 / 全员 | 9.28–10.1 | ⏸ 待开启/网盘进行 | 附件 2/3/5 定稿已归档 `docs/notification/`；附件 5 要求的 Model Card 口径待全队决策（见第五节）。**数字引用规则（9.21 更新）**：ρ=0.3665 / AUC=0.7812 / p=1.10e-9（错误记录）**绝对禁引**；ρ=0.414 仅可用于指称 v2.0 冻结模型 full_0916，且必须注明"487 行、裁决前口径、对 indel=1 行敏感"；现行 16.1 数据口径 = 锚定 LOGO-CV 中位 ρ=+0.310（train969，12/17 折），引用须注明未达 ρ≥0.5；对外交付采用哪个口径由全队会签确定（CHANGELOG 9.21 条第 8 款）。 |
| PPT 制作 + 录音台词 | 生D / 全员 | 9.30 | ⏸ 待开启/网盘进行 | 同上数字口径。 |
| 演示视频录制 | 生D / 计B | 10.1 | ⏸ 待录制 | 计B 已提供截图与走查路线。 |
| **最终材料提交（硬截止）** | 生D | 10.4 | ⏸ 待提交 | 时间充足。 |

---

## 三、跨组接口交接履约审计表（F1 – F7）

对照《分工详案_总控》（docs/plans/division_plan_master.md）第二节定义的 7 个关键交接接口：

| 接口 | 交付方 $\rightarrow$ 接收方 | 交付内容 | 计划死线 | 当前履约情况 |
|:---:|:---:|---|:---:|---|
| **F1** | 生A $\rightarrow$ 计A | Hi-TOM 清洗表（12 列标准） | 9.9 晚 | ✅ **已履约并三轮升级**：现行事实源 = 表级 `data/1_Hi-results-16.1-efficiency-20260921.xlsx`（1368 行，A/B/D 分级 + 处理状态 + 效率分）+ 模型输入 `data/hitom/hitom_seq30_merged_0918.csv`（1361 行）+ 裁决 `results/excluded_gids_final_0919.csv`（360 gid）。旧版 hitom_clean/seq30 各代留档。 |
| **F2** | 生B $\rightarrow$ 计B | 莴苣 T2T 基因组 + 注释 GFF3 | 9.21 晚 | ✅ **已履约**：基因组已索引，全基因组扫描闭环。 |
| **F3** | 生B $\rightarrow$ 计B | 着丝粒坐标 + NLR 基因清单 | 9.23 晚 | ✅ **已履约**：661 NLR 回填，demo 49 基因表生成。 |
| **F4** | 计A $\rightarrow$ 计B | 模型预测接口（`predict.py` + 模型权重） | 9.17 晚 | 🟡 **双重滞后**：运行时 CRISPRon 仍为近似公式（docstring 标注）；默认权重仍为 0916 旧口径。随 16.1 重训一并闭环（P0）。 |
| **F5** | 计A $\rightarrow$ 生D | 模型卡（`model_card.md`） | 9.19 晚 | 🟡 **已交付，口径待决策**：`model_card_full_0916.md` 基于 487 行 / ρ=0.414（v2.0 冻结口径）；随生产模型口径决策重写（16.1）或补注口径限定 + 现行评估值。 |
| **F6** | 计B $\rightarrow$ 生C | 候选 gRNA 结果表（供生物学核查） | 9.24 晚 | ✅ **已履约**：19,839 条候选表 + 脱靶/着丝粒标注 + `efficiency_score_full_0916` 列（重打分后需换列）。 |
| **F7** | 全员 $\rightarrow$ 生D | 报告、PPT 与申报素材集中汇总 | 9.28 齐 | 🟡 **部分就绪**：CS 侧素材、扫描/脱靶数据、截图、审计链、数据版本链说明齐备；模型指标答辩口径按本报告 6.4 表与第四节数字禁令执行；生物学文案待齐。 |

---

## 四、当前可直接运行与验收的交付物清单

如果评审专家或团队负责人现在检查代码仓库，**以下成果可以直接运行验证**：

1. **Streamlit 演示 Demo（Tab1 检索 + Tab2 实时打分）**
   - 启动命令：
     ```bash
     cd cs_pipeline
     conda run -n grna-demo streamlit run app/app.py
     ```
   - Tab1 展示 300+ 条候选 gRNA（脱靶数、着丝粒过滤、`efficiency_score_full_0916` 效率分）；Tab2 子进程真实 DeepSpCas9 打分（71.25 / 46.28 基准可复现）。⚠️ 免责文案中 ρ=0.414 为旧口径，待重训后更新。
2. **基因组与脱靶全流程处理脚本**
   - `scripts/07_scan_lettuce.py`（320 秒扫完全基因组）、`scripts/09_aggregate_offtarget.py`（600 万脱靶聚合）、`demo/prepare_demo_data.py`（自动装配）。
3. **现行数据治理与评估管线（9.21，全部带断言自检、可复现）**
   - 修正链：`scripts/dev/b_fix_16_postruling_0921.py`（9.19 裁决落地 + 效率分去抖动）→ `b_fix_161_pending_grades_0921.py`（guide候选表补定级 22 行）→ `b_crosscheck_0921.py`（回传文件交叉核对：guide候选复推 219/219、14→15 谱系、(4)版核验）；
   - 评估链：`scripts/dev/b_anchor_161_0921.py`（ruling1005/train969/noB879 × raw/anchor，含批次偏移锚定与 round(6) 常数折守卫）→ `results/b_anchor_161_0921.csv`；
   - 历史链：`scripts/10~13`（0916 全量重跑管线）与 `b_anchor_final_0919.py`（0919 裁决锚定）留档可复跑。
4. **已落盘的现行成果文件**
   - 数据交付版：`data/1_Hi-results-16.1-efficiency-20260921.xlsx`（版本链 12→13-merged→14→15→16→16.1，各版原件均保留）；
   - 审计与规则：`results/b_audit_0919.md`、`results/b_audit_0920.md`、`docs/reports/scoring_rules_14-15_0920.md`、`docs/reports/scoring_rules_16_post_ruling_0921.md`、`docs/reports/bio_lead_checklist_0920.md`（检查清单，guide候选表已就位、可发出执行）；
   - 指标：`results/b_anchor_161_0921.csv`（现行）、`b_anchor_final_0919.csv`、`b_sensitivity_logo_0919.csv`；
   - 工程冻结：`results/scan_stats_0923.md`、`offtarget_runlog_0924.md`、`offtarget_counts_0924.csv`、`demo_screenshots_0926/`；
   - 旧口径留档（勿引用）：`meta_model_ridge_full_0916.joblib`、`model_card_full_0916.md`、`logo_cv_full_0916.csv`。

---

## 五、下一步行动路线图（9.21 复核后重订）

9.17 版路线图的判断「卡点收敛为 guide 多样性」经扩表检验**依然成立且更清晰**：行数从 487 翻到 969（训练集），distinct guide 只从 23 涨到 35。

```
              【当前真实卡点：guide 多样性（扩表后仍在，且无外部增量可用）】

969 训练行 / 17 基因组 / 仅 35 条 distinct guide
        │
        ├─ 5 个基因只有 1 条 guide ──→ LOGO 5 折无法定义 ρ（12/17 折有效）
        ├─ 最大并列组 239 行同一 guide ──→ 特征全同，基因内无排序信号
        └─ 扩表 877 行只新增 12 条 guide（23→35）
        │
        ▼
结论：堆同 guide 重复行无效（0918 merged 全表 LOGO -0.257 已实证）
      公开数据混合预案 9.17 已两轮执行（人源 23,902 条 / 番茄 420 条）
      ——均"无害但无增量"；同物种/同科检索穷尽（自有 23 条已是
      该物种最大 per-guide 效率集）→ 达标出路已不存在，
      答辩叙事 = 迁移衰减三段对照 + 工程链路完整 + 数据规模受限的诚实说明
```

### 1. 计A 必做项（按优先级）
- ~~P0 启动公开数据混合预案~~：**已执行并终结（9.17，两轮）**——人源 Luo2020_Kim2019（23,902 条，50:1~2000:1 权重扫描）与番茄 Cucuy（420 条）混合均"无害但无增量"；同物种/同科穷尽检索确认自有 23 条 guide 已是该物种最大 per-guide 效率集。**不再重启**，结论与数据见 CHANGELOG 9.17 各条、`results/transferability_0917.md`。
- **P0 全队决策项：生产模型口径切换**——是否以 16.1 口径（train969，或老师追认弱信号后的 1005）重训替换 v2.0 冻结的 `meta_model_ridge_full_0916.joblib`（487 行裁决前口径）：
  - 若重训：落盘新 joblib → 出具单模型 vs 集成正式对比表 → 重写模型卡（F5）→ F4/demo 换权重、重打分、免责文案更新 → 重新冻结 tag `v2.1-freeze` 并登记 CHANGELOG。技术上即做即得（评估框架 `b_anchor_161_0921.py` 现成，训练流程沿用 `scripts/13` 改人群）；
  - 若维持冻结：模型卡与 demo 免责文案必须显式标注"训练集=487 行、裁决前口径"，并同时披露 16.1 口径现行评估值（锚定 +0.310），两口径不得混用。
- **P0（残留）修 `predict.py` 运行时 CRISPRon 特征**：第 79 行近似公式改为经 WSL 真实调用（`env/run_crispron_wsl.sh` 可用），或从特征集移除 `crispron_score` 后重训——无论上一条决策结果如何都必须闭环，正式提交前完成。
- **P1 双 gRNA 块 63 行 -A/-B 拆分**：切点反推副 guide、不需台账；拆分前后各跑一版 LOGO 量化影响（拆分前建议训练降权，16.1 表已带标记）。
- ~~P1 以 16.1 口径重跑锚定 + LOGO~~：**已完成（9.21）**——`b_anchor_161_0921.py` / `.csv`，见 6.4。
- ~~P1 评估口径纠正 / 补 F5 模型卡 / P2 核对 efficiency_norm~~：已完成（9.16）；模型卡口径随上面的决策项处理。

### 2. 计B / 生D 协同项
- **生D（PM）**：`CHANGELOG_0927.md` 9.18–9.21 段**已补写完成（9.21）**，待全队过一遍并会签（重点：第 8 款生产模型口径决策点）；处理 `v1.0-freeze` tag 缺失；**数字引用规则**：ρ=0.3665 / AUC=0.7812 / p=1.10e-9（错误记录）绝对禁引；ρ=0.414 仅限指称 v2.0 冻结模型且注明"487 行、裁决前口径"；现行 16.1 数据口径 = 锚定 LOGO-CV 中位 ρ=+0.310（train969，12/17 折），须注明未达 ρ≥0.5；对外采用哪个口径由会签确定。答辩叙事基调（CHANGELOG 9.17 定调）：「迁移可行性是数据集特异的三段对照（本氏烟成功 / 番茄失效 / 橡胶草部分）+ 工程链路完整 + 数据规模受限的诚实说明」。
- **计B**：demo 免责文案与供分列随生产模型口径决策同步更新（当前仍引用 0.414/`efficiency_score_full_0916`）；~~813 行编号地雷文件加 `_DEPRECATED` 标注~~ **已完成（9.21）**：`scores_merged_merged_0918_DEPRECATED.csv` / `feature_matrix_merged_0918_DEPRECATED.csv`（改名留档，禁止按 guide-id 跨文件 join，详见 CHANGELOG 9.21 条第 6 款）。
- **生A / 生B / 生C（生物侧）**：① 生物负责人检查清单（`docs/reports/bio_lead_checklist_0920.md`）现在可发出执行——guide候选表已回传就位；② **弱信号 36 行交老师追认**，附实证：剔除后锚定 LOGO 由 -0.078 → +0.310（弱信号行 guide 身份不明，属特征噪声源）；追认结果决定训练集 969 / 1005；③ **向老师补要 9.19 裁决书面记录**（现存唯一载体是 `excluded_gids_final_0919.csv` 与脚本注释，"(4).xlsx" 已证实为无批注的重复副本）；④ mR1 编号含义（2 行）说明；⑤ oligo 合成记录若能拿到仍建议留存（不阻塞）。

---

## 六、9.18–9.21 进展纪事与现行口径

> 本节为数据治理链路的详细纪事与指标全景；行动项统一见第五节（不再单列）。

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
- guide候选表（61 条 / 35 ref，在 `1_Hi-results-13-merged-20260918_计B批注版.xlsx`）已回传：15 版 219 行非剔除"待设计表确认"分级复推 **219/219 一致**、判定依据引用热点分数 0 不符；22 行"待定"补定级（16 行 refM Top1=68077→A/80；6 行 refSP1 Top1=62→弱信号 D/25）；生物负责人检查清单第一节自此可执行

### 6.4 模型指标全景（诚实口径，9.21 更新）

| 口径 | n 行 | LOGO-CV 中位 ρ | 备注 |
|---|---|---|---|
| 0916 full（v2.0 冻结模型口径） | 487 | 0.414 | 对 indel=1 行极敏感：去掉 101 行 → 0.596；去掉 USR-8145 → 0.477（`b_sensitivity_logo_0919.csv`）；引用仅限指称冻结模型且注明旧口径 |
| 0918 merged 全表 | 813 | -0.257 | 未剔 QC，噪声主导（`logo_cv_merged_0918.csv`）；实证"堆行数无效" |
| 0918 confident | 544 | 0.247 | （`logo_cv_confident_0918.csv`） |
| 0919 裁决后 raw / anchor | 1005 | -0.262 / -0.079 | `b_anchor_final_0919.csv` |
| **0921 复跑 ruling1005** | 1005 | raw -0.220 / anchor -0.078 | `b_anchor_161_0921.py` 代码路径同 0919，复现于浮点噪声级（13/18 折） |
| **0921 train969（16.1 训练集，现行最好）** | 969 | raw -0.248 / anchor **+0.310** | 剔弱信号 36 行后锚定 -0.08→+0.31，**弱信号剔除的实证支持**（12/17 折） |
| 0921 noB879（去 B 级 90 行） | 879 | raw +0.366 / anchor +0.297 | 有效折掉到 9~10/16，中位数与上两行可比性弱；锚定口径下 B 级影响小（0.310→0.297），与"预期很小"一致 |

**结论：ρ≥0.5 在所有口径下均未达标**，现行最好 = train969 锚定 **+0.310**。结构性瓶颈见第五节框图（35 条 distinct guide / 5 个单 guide 基因 / 最大并列 239 行）。
