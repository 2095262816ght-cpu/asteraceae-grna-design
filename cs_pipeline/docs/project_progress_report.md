# 菊科菊苣族 gRNA 设计工具项目进展全景审计报告

> **依据文档**：
> - [`docs/plans/project_plan_v3_condensed_0907.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/project_plan_v3_condensed_0907.md)（主方案）
> - [`docs/plans/division_plan_master.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_master.md)（甘特图与接口规范）
> - [`docs/plans/division_plan_cs.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_cs.md)（技术实施标准）
> - 计算机系流水线全量代码与产物目录：[`cs_pipeline/`](file:///d:/lifesciencechallenge/cs_pipeline/)
> 
> **审计基准时点**：2026-09-13 复核（最新 commit `914c86f` / tag `v1.1-freeze`，2026-09-12 22:58）
>
> **⚠️ 本报告 9-12 22:01 的初版把阶段 1/2 全部判为「未产出」，但当晚 22:11–22:57 计A 已把全链路跑完并落盘。本次复核据实改写状态；同时复核发现模型指标不达标且存在有效样本量问题，详见第一节、第二节阶段 1/2 表格与第五节。**

---

## 一、执行摘要：我们在哪里？

工程链路（计B）与算法链路（计A）均已跑通并落盘，但**算法链路的产出结果不成立**：模型指标未达标，且训练数据的有效样本量被严重高估。

```mermaid
graph TD
    classDef done fill:#d4edda,stroke:#28a745,color:#155724;
    classDef bad fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef pend fill:#fff3cd,stroke:#ffc107,color:#856404;

    A[阶段0: 数据清洗与环境搭建]:::done --> B[阶段1: 预训练模型打分与D2可行性]:::bad
    B --> C[阶段2: Stacking岭回归训练与评估]:::bad
    C -->|F4 predict.py 已交付| D[阶段3: 莴苣工具化与Streamlit Demo]:::done
    D --> E[阶段4: 成果冻结与交付冲刺]:::pend

    subgraph 计B负责: 已闭环且指标可信
        D
        F[全外显子/启动子扫描 13.87M]:::done
        G[Cas-OFFinder 脱靶 6.08M]:::done
        H[Streamlit 双Tab交互与截图]:::done
        I[10.3 匿名化检查与代码打包]:::done
    end

    subgraph 计A负责: 已跑通但结果不成立 🔴
        B
        C
        J[双模型批量打分: 260行仅8条唯一guide]:::bad
        K[D2 迁移 ρ: 去重后为负且不显著]:::bad
        L[Stacking 测试集 ρ=-0.3435 AUC=0.3672]:::bad
    end
```

### 核心结论速览
1. **计B（工程与工具链）已超前打穿至 10.3 交付状态，指标可信**：
   - 莴苣 T2T 全基因组 45,770 基因扫描完成（13,867,270 条候选）；
   - Cas-OFFinder 本地脱靶预测完成（19,839 条 demo gRNA，608 万脱靶位点）；
   - Streamlit demo 界面、预制数据、7 张演示截图、使用说明全部就绪；
   - 9.27 指标冻结记录、代码打包规范、10.3 匿名化专项检查（零命中）已全部做完。
2. **计A（算法模型链条）已于 9-12 晚跑通全部 5 步，但结果不可用，构成当前唯一致命卡点**：
   - 双模型打分表、D2 报告、特征矩阵、`meta_model_ridge_0919.joblib`、对比表、LOGO-CV、`predict.py` 接口均已落盘，`demo/app_data.csv` 19,839 条候选已写入 `efficiency_score`；
   - **但 `scores_merged_0911.csv` 260 行中唯一 `seq30` 只有 8 条（7 个基因），其余全为重复测定**，上游 `hitom_clean_v1.csv` 307 行也仅 12 个唯一 `seq20`。有效样本量是 8，不是 260；
   - **D2 迁移性未被证明**：全表 ρ=0.3308/0.3808（p=4.67e-8 / 2.13e-10）可复现，但按唯一 guide 去重后为 ρ=-0.2381 (p=0.57) / -0.0952 (p=0.82)，原「≥0.30 达标」判定已在 D2 报告中撤回；
   - **Stacking 未达标**：`model_comparison_0919.csv` 实际为测试集 ρ=-0.3435、AUC=0.3672（低于随机），单模型 ρ=-0.3545 / -0.2889，LOGO-CV 中位 -0.2254（7 折中 5 折无法计算），距 ρ≥0.5 达标线很远；
   - **`predict.py` 的 `crispron_score` 是人工线性式**（`deepspcas9_score*0.95 + (tm-50)*0.25`，第 76 行），并未调用 CRISPRon，与训练表中的真实 CRISPRon 分不同源，属推理期特征伪造；
   - **`CHANGELOG_0927.md` 曾冻结一组不存在的数字**（ρ=0.3665 / AUC=0.7812 / p=1.10e-9），已于 9.13 按实际产物更正并补记原因；
   - 因此 demo Tab1 的 `efficiency_score` 列当前不构成可信的效率预测，对外演示需降级为占位分或加显著免责说明。

---

## 二、全员里程碑与甘特表逐项对比（阶段 0 – 阶段 4）

### 阶段 0：数据盘点 + 环境准备（9.7 – 9.9 · 计划工时 9h）
**目标**：Hi-TOM 数据清洗定档 D1，conda 环境装配，验证预训练单序列打分。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| Hi-TOM 原始数据清洗与 12 列规范 | 生A | 9.8 晚 | ✅ 已完成 | 产出 [`cs_pipeline/data/hitom/hitom_clean_v1.csv`](file:///d:/lifesciencechallenge/cs_pipeline/data/hitom/hitom_clean_v1.csv)（307 行有效数据，剔除 113 行空白，空 guide_id 已补全）。 |
| 补齐 30bp 上下文序列 | 计A | 9.9 晚 | ✅ 已完成 | 坐标路线不通，改走 CDS 映射，产出 [`cs_pipeline/data/hitom/hitom_seq30_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/data/hitom/hitom_seq30_0909.csv)（260 行断言全过；47 行未匹配存 [`cs_pipeline/results/seq30_unmatched_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/seq30_unmatched_0909.csv)）。 |
| conda 主环境与 demo 环境搭建 | 计A / 计B | 9.9 晚 | ✅ 已完成 | `crispr`（py3.10+genet+TF2.9）与 `grna-demo` 环境已分离；CRISPRon Windows 原生路线与 WSL 路线均通（[`cs_pipeline/docs/reports/A0_work_report_0909.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/reports/A0_work_report_0909.md)）。 |
| 示例序列打分验证 | 计A | 9.9 晚 | ✅ 已完成 | DeepSpCas9 打出 71.2494（基准 71.25）；CRISPRon 原生打出 59.61（341 条官方测试逐字节一致）。 |
| **决策点 D1（路线定档）** | 全员 | 9.8 晚 | ✅ 已定案 | 有效数据 307 条（可打分 260 条），卡在 $\ge 300$ 条边缘。团队定案走**纯 Stacking**，不碰复杂的神经网络微调。 |

---

### 阶段 1：预训练模型批量打分 + 迁移可行性 D2（9.10 – 9.12 · 计划工时 9h）
**目标**：用两个预训练模型给自有橡胶草数据打分，评估其在植物上的迁移相关系数（Spearman $\rho$）。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| DeepSpCas9 批量打分 | 计A | 9.10 | ✅ 已产出 | [`02_score_deepspcas9.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/02_score_deepspcas9.py) 已跑，落盘 `results/scores_deepspcas9_0910.csv`（260 行）。 |
| CRISPRon 批量打分 | 计A | 9.11 | ✅ 已产出 | [`03_score_crispron.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/03_score_crispron.py) 经 WSL 实跑，落盘 `results/scores_crispron_0911.csv`（260 行），合并表 `scores_merged_0911.csv`。 |
| 预备公开数据集 Table S1 | 计A | 9.11 | ❌ 未入库 | `cs_pipeline/data/deepspcas9_tableS1.xlsx` 仍不存在；因 D2 判定被撤回，该混合预案现已成为必需项。 |
| **决策点 D2（迁移可行性结论）** | 计A / 生C | 9.12 | 🔴 已出结论但被撤回 | [`transferability_D2_0912.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/transferability_D2_0912.md) + `scatter_D2_0912.png` 已产出。全表 ρ=0.3308/0.3808 可复现，但 260 行仅含 **8 条唯一 seq30**，去重后 ρ=-0.2381 (p=0.57) / -0.0952 (p=0.82)，原「≥0.30 达标、无需混合预案」判定不成立，报告已加「〇、9.13 更正补记」。 |
| `efficiency_norm` 列口径 | 生A / 计A | 9.11 | ⚠️ 待核对 | 该列与 `indel_pct` 逐行完全相同（实为复制），而 [`04_spearman_D2.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/04_spearman_D2.py) 注释要求用生A 的批次内百分位、「一律不得用 indel_pct 重算」。 |

---

### 阶段 2：Stacking 模型构建 + 评估（9.13 – 9.19 · 计划工时 21h）
**目标**：提取序列与模型特征，组装元模型，按基因防泄漏分组调参，出具 LOGO-CV 与对比表。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 特征矩阵组装 | 计A | 9.14 | ✅ 已产出 | [`05_features.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/05_features.py) 已跑，`results/feature_matrix_0913.csv` 与 `feature_matrix_0914.csv` 落盘（260 行 × 27 列，其中入模特征 9 维）。 |
| 按基因防泄漏分组训练岭回归 | 计A | 9.17 | ✅ 已跑 / ❌ 未达标 | [`06_train_stacking.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/06_train_stacking.py) 已跑，`results/meta_model_ridge_0919.joblib` 已生成；GroupShuffleSplit 按基因分组、无泄漏断言通过。但测试集 ρ=-0.3435，远低于 ρ≥0.5 达标线。 |
| 模型交接接口 F4（`predict.py`） | 计A $\rightarrow$ 计B | 9.17 晚 | ⚠️ 已交付但有伪造特征 | [`predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) 已实现 `predict_efficiency` / `predict_details`，计B 已接通。但第 76 行的 `crispron_score` 是 `deepspcas9_score*0.95 + (tm-50)*0.25` 的人工线性式，未调用 CRISPRon，与训练特征不同源。 |
| 留一基因交叉验证（LOGO-CV） | 计A | 9.16 | ⚠️ 已产出但多数折无效 | `results/logo_cv_0916.csv` + `logo_cv_box_0916.png`。7 折中 5 折因留出基因内突变率恒定而 ρ 为空，仅 2 折可算（-0.3256 / -0.1252），中位 -0.2254。 |
| 模型对比表（单模型 vs 集成 $\rho$/AUC） | 计A | 9.19 | ❌ 未达标 | `results/model_comparison_0919.csv`：Stacking ρ=-0.3435 / AUC=0.3672；DeepSpCas9 ρ=-0.3545 / AUC=0.3672；CRISPRon ρ=-0.2889 / AUC=0.3828。AUC 低于随机，$\rho \ge 0.5$ 未达，应触发公开数据加权混合预案。 |
| 模型卡（Model Card）归档 | 计A $\rightarrow$ 生D | 9.19 晚 | 🔴 未产出 | 接口 F5 `model_card_0919.md` 仍缺失；且现有指标不达标，模型卡须如实写明局限性与有效样本量（8 条唯一 guide）。 |

---

### 阶段 3：莴苣工具化 + Streamlit Demo（9.20 – 9.26 · 计划工时 21h）
**目标**：下载莴苣 T2T 基因组，全外显子/启动子候选扫描，Cas-OFFinder 离线脱靶过滤，Streamlit 交互界面交付。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 莴苣 T2T 基因组与 GFF3 索引 | 生B $\rightarrow$ 计B | 9.21 晚 | ✅ 已完成 | 存放于本地 `cs_pipeline/data/lettuce/`（大文件按规范不进 git）。 |
| 着丝粒坐标 + NLR 基因清单 | 生B $\rightarrow$ 计B | 9.23 晚 | ✅ 已完成 | 回填 661 个 de novo NLR 基因坐标，选定 49 个代表基因（[`cs_pipeline/data/demo/demo_nlr50_genes.txt`](file:///d:/lifesciencechallenge/cs_pipeline/data/demo/demo_nlr50_genes.txt)）。 |
| 莴苣全基因组 gRNA 扫描（脚本 07） | 计B | 9.23 | ✅ 已完成 | [`cs_pipeline/scripts/07_scan_lettuce.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/07_scan_lettuce.py) 完成，45,770 个基因扫描出 13,867,270 条候选，耗时 320 秒（详见 [`cs_pipeline/results/scan_stats_0923.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/scan_stats_0923.md)）。 |
| Cas-OFFinder 脱靶位点分析（脚本 08/09） | 计B | 9.24 | ✅ 已完成 | 对 demo 范围 19,839 条 gRNA 运行脱靶（GPU 分批），检出 6,088,827 个位点，汇总生成 [`cs_pipeline/results/offtarget_counts_0924.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_counts_0924.csv)。 |
| Streamlit Demo 界面开发 | 计B | 9.25 | ✅ 已完成 | [`cs_pipeline/app/app.py`](file:///d:/lifesciencechallenge/cs_pipeline/app/app.py) 交付。支持 Tab1 基因检索（耗时仅 4ms）与 Tab2 实时子进程打分（DeepSpCas9 耗时 24.1s）。 |
| Demo 走查与截图留痕 | 计B | 9.26 | ✅ 已完成 | 3 个真实基因端到端走查，7 张真实无敏感信息截图已落盘于 [`cs_pipeline/results/demo_screenshots_0926/`](file:///d:/lifesciencechallenge/cs_pipeline/results/demo_screenshots_0926/)。 |

---

### 阶段 4：交付冲刺（9.27 – 10.4 · 计划工时 24h）
**目标**：指标冻结、代码清理脱敏、报告/PPT/视频制作、匿名化合规审核、最终提交。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| **指标冻结与代码打 Tag** | 生D / 计B | 9.27 🔶 | ⚠️ 已冻结但记录曾被更正 | [`CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md) 冻结了扫描与脱靶数字（可信）；tag `v1.1-freeze` 已打，但 `v1.0-freeze` 本地缺失。模型三项指标原记录（ρ=0.3665 / AUC=0.7812 / p=1.10e-9）与实际产物不符，9.13 已按 `model_comparison_0919.csv` 更正并补记原因。 |
| 源码整理与运行说明 | 计B | 10.2 | ✅ 已提前就绪 | [`cs_pipeline/README.md`](file:///d:/lifesciencechallenge/cs_pipeline/README.md)、[`requirements.txt`](file:///d:/lifesciencechallenge/cs_pipeline/requirements.txt) 已重写并通过干净环境验证。 |
| **匿名化专项检查（红线）** | 全员 / 计B | 10.3 🔶 | ✅ CS侧已提前通关 | 详见 [`cs_pipeline/docs/reports/anonymization_checklist_1003.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/reports/anonymization_checklist_1003.md)，代码、注释、提交者（`team`）、截图路径等全部零命中。 |
| 评审表/报告书主稿 | 生D 主笔 / 全员 | 9.28–10.1 | ⏸ 待开启/网盘进行 | 代码库中暂无 Word/PDF 主件（按规范存于团队共享网盘 `LSC_共享/deliverables/`）。 |
| PPT 制作 + 录音台词 | 生D / 全员 | 9.30 | ⏸ 待开启/网盘进行 | 同上。 |
| 演示视频录制 | 生D / 计B | 10.1 | ⏸ 待录制 | 计B 已提供 7 张截图与走查路线，录屏待生物系/PM 统筹执行。 |
| **最终材料提交（硬截止）** | 生D | 10.4 | ⏸ 待提交 | 距离截止仍有充足时间。 |

---

## 三、跨组接口交接履约审计表（F1 – F7）

对照《分工详案_总控》（docs/plans/division_plan_master.md）第二节定义的 7 个关键交接接口：

| 接口 | 交付方 $\rightarrow$ 接收方 | 交付内容 | 计划死线 | 当前履约情况 |
|:---:|:---:|---|:---:|---|
| **F1** | 生A $\rightarrow$ 计A | Hi-TOM 清洗表（12 列标准） | 9.9 晚 | ✅ **已履约**：`data/hitom/hitom_clean_v1.csv` + `hitom_seq30_0909.csv` 已入库。 |
| **F2** | 生B $\rightarrow$ 计B | 莴苣 T2T 基因组 + 注释 GFF3 | 9.21 晚 | ✅ **已履约**：基因组已索引，全基因组外显子/启动子扫描已闭环。 |
| **F3** | 生B $\rightarrow$ 计B | 着丝粒坐标 + NLR 基因清单 | 9.23 晚 | ✅ **已履约**：回填完成，生成 demo 专用的 49 个 NLR 基因表。 |
| **F4** | 计A $\rightarrow$ 计B | 模型预测接口（`predict.py` + 模型权重） | 9.17 晚 | ⚠️ **形式履约、实质不可用**：`predict.py` 已实现，`meta_model_ridge_0919.joblib` 已交付，demo 已接通；但接口内 `crispron_score` 为人工线性式（非 CRISPRon 真实输出），且模型测试集 ρ=-0.3435 未达标，供分结果不可作为效率预测使用。 |
| **F5** | 计A $\rightarrow$ 生D | 模型卡（`model_card.md`） | 9.19 晚 | 🔴 **未履约**：`model_card_0919.md` 仍缺失。补写时须如实记录真实 ρ/AUC、9 维入模特征顺序、有效样本量（8 条唯一 guide）与 CRISPRon 特征伪造问题。 |
| **F6** | 计B $\rightarrow$ 生C | 候选 gRNA 结果表（供生物学核查） | 9.24 晚 | ✅ **已履约**：19,839 条 demo 候选表已合成，脱靶与着丝粒标注齐全。 |
| **F7** | 全员 $\rightarrow$ 生D | 报告、PPT 与申报素材集中汇总 | 9.28 齐 | 🟡 **部分就绪**：CS 侧工具链素材、扫描脱靶数据、Demo 截图已备齐；模型指标与生物学文案待齐。 |

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
     - 切换到 Tab2，输入两条 30bp 序列，子进程调用 DeepSpCas9 实测打分（返回 71.25 / 46.28）。
   - ⚠️ **验收时须注意**：Tab1 的「效率分（Stacking预测）」列（`demo/app_data.csv` 的 `efficiency_score`，19,839 条已全量写入）来自一个测试集 ρ=-0.3435、AUC=0.3672 的未达标模型，且该模型的 `crispron_score` 输入在 `predict.py` 中是人工线性式而非真实 CRISPRon 输出。**此列当前不具备效率预测效力**，对外演示应回退到 `efficiency_placeholder` 或在界面上加显著说明。Tab2 的 DeepSpCas9 分是真实推理，可正常演示。
2. **基因组与脱靶全流程处理脚本**
   - [`cs_pipeline/scripts/07_scan_lettuce.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/07_scan_lettuce.py)：已验证可 320 秒扫完整基因组；
   - [`cs_pipeline/scripts/09_aggregate_offtarget.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/09_aggregate_offtarget.py)：已验证可聚合 600 万条脱靶原始记录；
   - [`cs_pipeline/demo/prepare_demo_data.py`](file:///d:/lifesciencechallenge/cs_pipeline/demo/prepare_demo_data.py)：已验证可自动装配 demo 所需数据。
3. **已落盘的冻结成果文件**
   - 扫描统计：[`cs_pipeline/results/scan_stats_0923.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/scan_stats_0923.md)
   - 脱靶日志：[`cs_pipeline/results/offtarget_runlog_0924.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_runlog_0924.md)
   - 脱靶计数：[`cs_pipeline/results/offtarget_counts_0924.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_counts_0924.csv)
   - Demo 运行截图 7 张：[`cs_pipeline/results/demo_screenshots_0926/`](file:///d:/lifesciencechallenge/cs_pipeline/results/demo_screenshots_0926/)

---

## 五、下一步行动路线图（9.13 复核后重订）

原路线图的 5 步（打分 → D2 → 特征 → 训练 → 接口）已在 9-12 晚全部执行完毕，**卡点已从「没跑」变成「跑出来的结果不成立」**。根因是数据，不是调参：

```
              【真实卡点：有效样本量】

hitom_clean_v1.csv 307 行  ──→  仅 13 组唯一 (seq20, pam)
        │                        其中 1 组占 141 行、2 组占 58/32 行
        ▼
CDS 匹配后 260 行        ──→  仅 8 条唯一 seq30（7 个基因）
        │
        ▼
补全 47 条未匹配 guide   ──→  至多再加 4 条唯一 guide，上限 12 条
        │
        ▼
结论：自有数据无论如何补全，都无法支撑 ρ≥0.5 的相关性检验
      唯一出路 = 详案规定的「公开数据加权混合」预案
```

### 1. 计A 必做项（按优先级）
- **P0 启动公开数据混合预案**：下载 DeepSpCas9 Table S1 入库 `data/deepspcas9_tableS1.xlsx`（详案规定的唯一扩充途径），与自有数据加权混合后重训 `06_train_stacking.py`，重新出具 ρ/AUC。
- **P0 修 `predict.py` 的 CRISPRon 特征**：第 76 行改为经 WSL 真实调用 CRISPRon（`env/run_crispron_wsl.sh` 已可用），或直接从 9 维特征集中移除 `crispron_score` 后重训；禁止保留人工线性式。
- **P1 评估口径纠正**：`04_spearman_D2.py` 与 `06_train_stacking.py` 须先按唯一 guide 聚合（同一 guide 的重复取 `indel_pct` 中位数），再计算 ρ；主指标改用 LOGO-CV，并在输出中同时给出 n（唯一 guide 数），避免再次出现 260 行的虚假显著性。
- **P1 补 F5 模型卡** `results/model_card_0919.md`：如实写明 9 维特征顺序、训练集版本、真实 ρ/AUC、有效样本量与已知局限。
- **P2 核对 `efficiency_norm`**：与生A 确认该列是否应为批次内百分位（当前与 `indel_pct` 完全相同），确认后重算 D2 与训练。

### 2. 计B / 生D 协同项
- **计B**：demo Tab1 的效率分列回退为 `efficiency_placeholder`，或保留 `efficiency_score` 但在界面加显著免责说明（「模型未达标，仅供流程演示」）；`app/app.py` 第 12 行的说明文字同步改口径。
- **生D（PM）**：`CHANGELOG_0927.md` 的 9.13 更正记录需全队过一遍并会签；补打缺失的 `v1.0-freeze` tag（或删除该条声明）；评审表与 PPT 中**不得引用 ρ=0.3665 / AUC=0.7812 / p=1.10e-9 这组数字**，模型指标以重训后的实际产物为准；若混合预案后仍未达标，答辩口径应转为「工程链路完整 + 数据规模受限的诚实说明」，而非硬报达标。
- **生A / 生C**：核对 47 条未命中 CDS 的 guide（[`seq30_unmatched_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/seq30_unmatched_0909.csv)）。注意此项**只能把唯一 guide 从 8 条提到至多 12 条**，不解决样本量问题，但可作为数据完整性交代；同时确认 Hi-TOM 原始交付是否还有未纳入本仓库的其他 guide 序列。

