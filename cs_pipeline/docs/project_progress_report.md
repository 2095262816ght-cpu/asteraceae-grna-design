# 菊科菊苣族 gRNA 设计工具项目进展全景审计报告

> **依据文档**：
> - [`docs/ImplementationScheme/项目执行方案_v3压缩版_0907.md`](file:///d:/lifesciencechallenge/docs/ImplementationScheme/%E9%A1%B9%E7%9B%AE%E6%89%A7%E8%A1%8C%E6%96%B9%E6%A1%88_v3%E5%8E%8B%E7%BC%A9%E7%89%88_0907.md)（主方案）
> - [`docs/ImplementationScheme/分工详案_总控.md`](file:///d:/lifesciencechallenge/docs/ImplementationScheme/%E5%88%86%E5%B7%A5%E8%AF%A6%E6%A1%88_%E6%80%BB%E6%8E%A7.md)（甘特表与接口规范）
> - [`docs/ImplementationScheme/分工详案_计算机系.md`](file:///d:/lifesciencechallenge/docs/ImplementationScheme/%E5%88%86%E5%B7%A5%E8%AF%A6%E6%A1%88_%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%B3%BB.md)（技术实施标准）
> - 计算机系流水线全量代码与产物目录：[`cs_pipeline/`](file:///d:/lifesciencechallenge/cs_pipeline/)
> 
> **审计基准时点**：2026-09-12（当前最新 commit `9369d5f`，前续 tag `v1.0-freeze` / commit `3312711`）

---

## 一、执行摘要：我们在哪里？

当前项目呈现出**「工程骨架超前就绪，核心模型算法严重滞后」**的结构性脱节状态：

```mermaid
graph TD
    classDef done fill:#d4edda,stroke:#28a745,color:#155724;
    classDef block fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef pend fill:#fff3cd,stroke:#ffc107,color:#856404;

    A[阶段0: 数据清洗与环境搭建]:::done --> B[阶段1: 预训练模型打分与D2可行性]:::block
    B --> C[阶段2: Stacking岭回归训练与评估]:::block
    C -->|缺失 F4 predict.py| D[阶段3: 莴苣工具化与Streamlit Demo]:::done
    D --> E[阶段4: 成果冻结与交付冲刺]:::pend

    subgraph 计B负责: 已超前闭环
        D
        F[全外显子/启动子扫描 13.87M]:::done
        G[Cas-OFFinder 脱靶 6.08M]:::done
        H[Streamlit 双Tab交互与截图]:::done
        I[10.3 匿名化检查与代码打包]:::done
    end

    subgraph 计A负责: 核心卡点 🔴
        B
        C
        J[DeepSpCas9 & CRISPRon 批量打分]:::block
        K[D2 迁移 Spearman ρ 计算]:::block
        L[Stacking 模型与 LOGO-CV]:::block
    end
```

### 核心结论速览
1. **计B（工程与工具链）已超前打穿至 10.3 交付状态**：
   - 莴苣 T2T 全基因组 45,770 基因扫描完成（13,867,270 条候选）；
   - Cas-OFFinder 本地脱靶预测完成（19,839 条 demo gRNA，608 万脱靶位点）；
   - Streamlit demo 界面、预制数据、7 张演示截图、使用说明全部就绪；
   - 9.27 指标冻结记录、代码打包规范、10.3 匿名化专项检查（零命中）已全部做完。
2. **计A（算法模型链条）卡在 9.10–9.19，处于全项目唯一且致命的阻塞点**：
   - 虽然单序列打分环境和脚本骨架已通，但**自有 260 条数据未正式运行打分输出**；
   - **决策点 D2（迁移可行性 Spearman $\rho$）未出具结论**；
   - **Stacking 岭回归元模型未训练**，`results/meta_model_ridge_0919.joblib` 不存在；
   - **接口 [`scripts/predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) 仍为 `raise NotImplementedError`**；
   - 当前 Demo 页面中的效率分只能使用启发式占位分（`efficiency_placeholder`），无法展示真正的 AI 集成模型分。

---

## 二、全员里程碑与甘特表逐项对比（阶段 0 – 阶段 4）

### 阶段 0：数据盘点 + 环境准备（9.7 – 9.9 · 计划工时 9h）
**目标**：Hi-TOM 数据清洗定档 D1，conda 环境装配，验证预训练单序列打分。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| Hi-TOM 原始数据清洗与 12 列规范 | 生A | 9.8 晚 | ✅ 已完成 | 产出 [`cs_pipeline/data/hitom_clean_v1.csv`](file:///d:/lifesciencechallenge/cs_pipeline/data/hitom_clean_v1.csv)（307 行有效数据，剔除 113 行空白，空 guide_id 已补全）。 |
| 补齐 30bp 上下文序列 | 计A | 9.9 晚 | ✅ 已完成 | 坐标路线不通，改走 CDS 映射，产出 [`cs_pipeline/data/hitom_seq30_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/data/hitom_seq30_0909.csv)（260 行断言全过；47 行未匹配存 [`cs_pipeline/results/seq30_unmatched_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/seq30_unmatched_0909.csv)）。 |
| conda 主环境与 demo 环境搭建 | 计A / 计B | 9.9 晚 | ✅ 已完成 | `crispr`（py3.10+genet+TF2.9）与 `grna-demo` 环境已分离；CRISPRon Windows 原生路线与 WSL 路线均通（[`cs_pipeline/docs/A0_工作报告_0909.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/A0_%E5%B7%A5%E4%BD%9C%E6%8A%A5%E5%91%8A_0909.md)）。 |
| 示例序列打分验证 | 计A | 9.9 晚 | ✅ 已完成 | DeepSpCas9 打出 71.2494（基准 71.25）；CRISPRon 原生打出 59.61（341 条官方测试逐字节一致）。 |
| **决策点 D1（路线定档）** | 全员 | 9.8 晚 | ✅ 已定案 | 有效数据 307 条（可打分 260 条），卡在 $\ge 300$ 条边缘。团队定案走**纯 Stacking**，不碰复杂的神经网络微调。 |

---

### 阶段 1：预训练模型批量打分 + 迁移可行性 D2（9.10 – 9.12 · 计划工时 9h）
**目标**：用两个预训练模型给自有橡胶草数据打分，评估其在植物上的迁移相关系数（Spearman $\rho$）。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| DeepSpCas9 批量打分 | 计A | 9.10 | 🟡 脚本就绪但未产出 | [`cs_pipeline/scripts/02_score_deepspcas9.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/02_score_deepspcas9.py) 已就绪，但结果文件 `results/scores_deepspcas9_0910.csv` 尚未落盘。 |
| CRISPRon 批量打分 | 计A | 9.11 | 🟡 脚本就绪但未产出 | [`cs_pipeline/scripts/03_score_crispron.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/03_score_crispron.py) 已就绪，但结果文件 `results/scores_crispron_0911.csv` 尚未落盘。 |
| 预备公开数据集 Table S1 | 计A | 9.11 | ❌ 未入库 | 计划下载备用的 `cs_pipeline/data/deepspcas9_tableS1.xlsx` 不存在。 |
| **决策点 D2（迁移可行性结论）** | 计A / 生C | 9.12 | 🔴 严重滞后 | 脚本 [`cs_pipeline/scripts/04_spearman_D2.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/04_spearman_D2.py) 依赖上述打分表。报告文件 `results/transferability_D2_0912.md` **不存在**，未出具 $\rho$ 值。 |

---

### 阶段 2：Stacking 模型构建 + 评估（9.13 – 9.19 · 计划工时 21h）
**目标**：提取序列与模型特征，组装元模型，按基因防泄漏分组调参，出具 LOGO-CV 与对比表。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 特征矩阵组装 | 计A | 9.14 | 🔴 未产出 | 脚本 [`cs_pipeline/scripts/05_features.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/05_features.py) 存在，但 `results/feature_matrix_0914.csv` 不存在。 |
| 按基因防泄漏分组训练岭回归 | 计A | 9.17 | 🔴 未产出 | 脚本 [`cs_pipeline/scripts/06_train_stacking.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/06_train_stacking.py) 存在，但模型权重 `results/meta_model_ridge_0919.joblib` 未生成。 |
| 模型交接接口 F4（`predict.py`） | 计A $\rightarrow$ 计B | 9.17 晚 | 🔴 阻塞 | [`cs_pipeline/scripts/predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) 仍是占位异常：`raise NotImplementedError`。 |
| 留一基因交叉验证（LOGO-CV） | 计A | 9.16 | 🔴 未产出 | `results/logo_cv_0916.csv` 缺失。 |
| 模型对比表（单模型 vs 集成 $\rho$/AUC） | 计A | 9.19 | 🔴 未产出 | `results/model_comparison_0919.csv` 缺失；是否达标（$\rho \ge 0.5$）未判定。 |
| 模型卡（Model Card）归档 | 计A $\rightarrow$ 生D | 9.19 晚 | 🔴 未产出 | 接口 F5 `model_card.md` 缺失。 |

---

### 阶段 3：莴苣工具化 + Streamlit Demo（9.20 – 9.26 · 计划工时 21h）
**目标**：下载莴苣 T2T 基因组，全外显子/启动子候选扫描，Cas-OFFinder 离线脱靶过滤，Streamlit 交互界面交付。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| 莴苣 T2T 基因组与 GFF3 索引 | 生B $\rightarrow$ 计B | 9.21 晚 | ✅ 已完成 | 存放于本地 `cs_pipeline/data/lettuce/`（大文件按规范不进 git）。 |
| 着丝粒坐标 + NLR 基因清单 | 生B $\rightarrow$ 计B | 9.23 晚 | ✅ 已完成 | 回填 661 个 de novo NLR 基因坐标，选定 49 个代表基因（[`cs_pipeline/data/demo_nlr50_genes.txt`](file:///d:/lifesciencechallenge/cs_pipeline/data/demo_nlr50_genes.txt)）。 |
| 莴苣全基因组 gRNA 扫描（脚本 07） | 计B | 9.23 | ✅ 已完成 | [`cs_pipeline/scripts/07_scan_lettuce.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/07_scan_lettuce.py) 完成，45,770 个基因扫描出 13,867,270 条候选，耗时 320 秒（详见 [`cs_pipeline/results/scan_stats_0923.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/scan_stats_0923.md)）。 |
| Cas-OFFinder 脱靶位点分析（脚本 08/09） | 计B | 9.24 | ✅ 已完成 | 对 demo 范围 19,839 条 gRNA 运行脱靶（GPU 分批），检出 6,088,827 个位点，汇总生成 [`cs_pipeline/results/offtarget_counts_0924.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/offtarget_counts_0924.csv)。 |
| Streamlit Demo 界面开发 | 计B | 9.25 | ✅ 已完成 | [`cs_pipeline/app/app.py`](file:///d:/lifesciencechallenge/cs_pipeline/app/app.py) 交付。支持 Tab1 基因检索（耗时仅 4ms）与 Tab2 实时子进程打分（DeepSpCas9 耗时 24.1s）。 |
| Demo 走查与截图留痕 | 计B | 9.26 | ✅ 已完成 | 3 个真实基因端到端走查，7 张真实无敏感信息截图已落盘于 [`cs_pipeline/results/demo_screenshots_0926/`](file:///d:/lifesciencechallenge/cs_pipeline/results/demo_screenshots_0926/)。 |

---

### 阶段 4：交付冲刺（9.27 – 10.4 · 计划工时 24h）
**目标**：指标冻结、代码清理脱敏、报告/PPT/视频制作、匿名化合规审核、最终提交。

| 任务项 | 负责角色 | 计划死线 | 当前状态 | 现状与证据 |
|---|---|:---:|:---:|---|
| **指标冻结与代码打 Tag** | 生D / 计B | 9.27 🔶 | 🟡 条件性冻结 | [`cs_pipeline/results/CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md) 已冻结扫描和脱靶数据，打下 `v1.0-freeze` tag；**但显式记录了计A 模型三项缺失**。 |
| 源码整理与运行说明 | 计B | 10.2 | ✅ 已提前就绪 | [`cs_pipeline/README.md`](file:///d:/lifesciencechallenge/cs_pipeline/README.md)、[`requirements.txt`](file:///d:/lifesciencechallenge/cs_pipeline/requirements.txt) 已重写并通过干净环境验证。 |
| **匿名化专项检查（红线）** | 全员 / 计B | 10.3 🔶 | ✅ CS侧已提前通关 | 详见 [`cs_pipeline/docs/匿名化检查清单_1003.md`](file:///d:/lifesciencechallenge/cs_pipeline/docs/%E5%8C%BF%E5%90%8D%E5%8C%96%E6%A3%80%E6%9F%A5%E6%B8%85%E5%8D%95_1003.md)，代码、注释、提交者（`team`）、截图路径等全部零命中。 |
| 评审表/报告书主稿 | 生D 主笔 / 全员 | 9.28–10.1 | ⏸ 待开启/网盘进行 | 代码库中暂无 Word/PDF 主件（按规范存于团队共享网盘 `LSC_共享/deliverables/`）。 |
| PPT 制作 + 录音台词 | 生D / 全员 | 9.30 | ⏸ 待开启/网盘进行 | 同上。 |
| 演示视频录制 | 生D / 计B | 10.1 | ⏸ 待录制 | 计B 已提供 7 张截图与走查路线，录屏待生物系/PM 统筹执行。 |
| **最终材料提交（硬截止）** | 生D | 10.4 | ⏸ 待提交 | 距离截止仍有充足时间。 |

---

## 三、跨组接口交接履约审计表（F1 – F7）

对照《分工详案_总控.md》第二节定义的 7 个关键交接接口：

| 接口 | 交付方 $\rightarrow$ 接收方 | 交付内容 | 计划死线 | 当前履约情况 |
|:---:|:---:|---|:---:|---|
| **F1** | 生A $\rightarrow$ 计A | Hi-TOM 清洗表（12 列标准） | 9.9 晚 | ✅ **已履约**：`data/hitom_clean_v1.csv` + `hitom_seq30_0909.csv` 已入库。 |
| **F2** | 生B $\rightarrow$ 计B | 莴苣 T2T 基因组 + 注释 GFF3 | 9.21 晚 | ✅ **已履约**：基因组已索引，全基因组外显子/启动子扫描已闭环。 |
| **F3** | 生B $\rightarrow$ 计B | 着丝粒坐标 + NLR 基因清单 | 9.23 晚 | ✅ **已履约**：回填完成，生成 demo 专用的 49 个 NLR 基因表。 |
| **F4** | 计A $\rightarrow$ 计B | 模型预测接口（`predict.py` + 模型权重） | 9.17 晚 | 🔴 **未履约（全线卡点）**：`predict.py` 仍为占位符，joblib 模型未交。 |
| **F5** | 计A $\rightarrow$ 生D | 模型卡（`model_card.md`） | 9.19 晚 | 🔴 **未履约**：特征重要性、$\rho$、AUC 报告均未归档。 |
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

## 五、下一步行动路线图（破局策略）

为了在 10 月 4 日前顺利提交高质量参赛作品，当前必须集中火力解决**计A 的模型断点**：

```
                    【当前破局最短路径】
                         
 1. 运行 02/03 脚本           2. 运行 04 计算 ρ          3. 组装 05 与训练 06
给自有 260 条数据打分   ───→  落盘 D2 可行性结论 ───→   按基因防泄漏调参
(DeepSpCas9 + CRISPRon)       (判定迁移效果)             产出 meta_model_ridge
                                                                │
                                                                ▼
 5. 追加 v1.1-freeze 标签    4. 打通 predict.py
全员进入报告与PPT冲刺    ←─── 接管 Demo Tab1 占位分
(生D / 生C / 答辩材料)        (实现真正 AI 集成打分)
```

### 1. 计A 紧急任务（预计耗时 3–4 小时）
- **步骤 1**：激活 `crispr` 环境，运行 [`02_score_deepspcas9.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/02_score_deepspcas9.py) 生成 `results/scores_deepspcas9_0910.csv`；
- **步骤 2**：激活 `crispron-win`（或 WSL），运行 [`03_score_crispron.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/03_score_crispron.py) 生成 `results/scores_crispron_0911.csv`；
- **步骤 3**：合并两表运行 [`04_spearman_D2.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/04_spearman_D2.py)，将两模型的 Spearman $\rho$ 记录到 `results/transferability_D2_0912.md`（完成 D2 里程碑）；
- **步骤 4**：运行 [`05_features.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/05_features.py) 提取特征矩阵，运行 [`06_train_stacking.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/06_train_stacking.py) 完成分组交叉验证并导出 `results/meta_model_ridge_0919.joblib`；
- **步骤 5**：实现 [`scripts/predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) 的 `predict_efficiency` 函数，打通与 demo 的对接。

### 2. 全员与生物系协同任务
- **生A**：核对 47 条未命中 CDS 的 guide（[`cs_pipeline/results/seq30_unmatched_0909.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/seq30_unmatched_0909.csv)），若能补全可进一步扩大训练集；
- **生D（PM）**：在获得真实的 Stacking 模型 $\rho$ 和对比指标后，补打 `v1.1-freeze` tag 并更新 [`CHANGELOG_0927.md`](file:///d:/lifesciencechallenge/cs_pipeline/results/CHANGELOG_0927.md)；同步开启评审表与 PPT 的撰写。
