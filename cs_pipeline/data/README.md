# 数据来源、许可与溯源说明（data/）

> 对应《附件5 代码提交要求》第三节「可复现性与溯源要求 — 数据」与第五节「数据或资源受限」。
> 本目录为**匿名评审交付版**：不含原始测序交付归档（`data/raw/`，未随包发布，见文末获取方式）。

---

## 一、数据资产清单：名称 / 版本 / 获取时间 / 用途 / 许可

### 1. 自有实测数据（核心训练标签来源）

| 名称 | 版本 / 文件 | 获取时间 | 用途 | 许可 |
|---|---|---|---|---|
| 橡胶草（*Taraxacum kok-saghyz*）Hi-TOM 靶向扩增子测序 | 原始交付 `data/raw/hitom/`（24 批次 / 1,368 行；**未随包发布**） | 2026-09-03 首批交付，09-18 追加 NEWdata | 训练 / 验证 / 测试标签（`indel_pct`）唯一来源 | **团队自有湿实验数据**，未公开发表、未对外授权；本次仅提交清洗后快照 |
| 清洗后主表 | `hitom/hitom_clean_v1.csv` → `hitom_clean_full_0916.csv` → `hitom_clean_merged_0918.csv` → `hitom_clean_confident_0918.csv` | 2026-09-09 ~ 09-18 | 各阶段训练集口径 | 同上 |
| 特征/标签合并表 | `hitom/hitom_seq30_*.csv`、`hitom_reads_depth_0921.csv` | 2026-09-09 ~ 09-21 | 10 维入模特征构建 | 同上 |
| 剔除与复算记录 | `hitom/usr5712_indel_rightside_recompute_0915.csv` | 2026-09-15 | indel 口径修正留档 | 同上 |

**许可说明**：上述实测数据由本项目湿实验团队产生，**不涉及第三方数据权益**；因含未发表实验结果，按赛事要求不上传原始测序归档（R0/R1 fastq、PCR 检测图），仅提交可复核的清洗后快照与清洗规则。

### 2. 外部公开数据（仅用于迁移性对照实验，**未进入生产模型训练**）

| 名称 | 版本 / 文件 | 条数 | 获取时间 | 用途 | 来源与许可 |
|---|---|---|---|---|---|
| 人源公开 gRNA 活性集（Luo2020 / Kim2019） | `hitom/public_luo2020_kim2019_clean.csv` | 23,902 | 2026-09-17 | 公开数据加权混合迁移实验（`scripts/14_public_mix_train.py`） | 文献补充材料公开数据，学术用途引用 |
| 番茄公开数据集（Cucuy，420 条） | `hitom/public_cucuy420_clean.csv` | 420 | 2026-09-17 | 同上（植物侧迁移对照） | 文献补充材料公开数据，学术用途引用 |
| 公开数据集（Gong，52 条） | `hitom/public_gong52_clean.csv` | 52 | 2026-09-17 | 同上 | 文献补充材料公开数据，学术用途引用 |
| DeepSpCas9 Table S1 | `hitom/` 派生 + 训练侧备用 | ~12,000 | 2026-09-11 | 公开数据预案备查 | Kim HK et al. *Sci. Adv.* 5, eaax9249 (2019) 补充材料 |

**结论（重要）**：公开数据混合已两轮执行（50:1~2000:1 权重扫描）均「无害但无增量」，**生产模型 `meta_model_hier_bb_nob879_0921.joblib` 未使用任何外部公开数据训练**，仅使用本项目自有 Hi-TOM 实测数据。证据见 `results/transferability_0917.md`、`results/CHANGELOG_0927.md` 9.17 各条。

### 3. 参考基因组与注释（输入参考，非训练数据）

| 名称 | 版本 / 文件 | 获取时间 | 用途 | 来源与许可 |
|---|---|---|---|---|
| 茎用生菜（*Lactuca sativa* var. *angustana*）基因组 v1.1c | `reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa` + `1-1_*.gff` + `1-3_*_ATAC_peaks.xlsx` | 2026-09-20 前 | 靶基因坐标、ATAC 开放区注释 | 随湿实验数据配套交付；学术用途 |
| 橡胶草 TKS 基因组 | `reference_genomes/2-1_TKS.genome.fasta` + `2-2_TKS.genome.gff3` | 2026-09-20 前 | Hi-TOM 靶位点坐标映射 | 同上 |
| 莴苣 T2T 完整基因组 | `reference_genomes/3-1_LsT2T.genome.fa` + `3-1_LsT2T.annotation.gff3` | 2026-09-21 | 全基因组候选扫描（`scripts/07_scan_lettuce.py` 直接输入） | **莴苣 T2T 论文 Figshare 页面公开下载**（fasta/GFF3），学术用途 |
| 着丝粒抑制区坐标 | `reference_genomes/T2T_Supplemental_Tables_7-9.xlsx` | 2026-09-23 | 脱靶风险抑制区过滤 | 莴苣 T2T 论文补充表，学术用途 |
| NLR 基因座 / 结构域注释 | `reference_genomes/nlr_gene_loci.csv`、`domain_annotations.csv`、`imports/` | 2026-09-08 ~ 09-24 | NLR 代表基因注释 | NLR-Annotator 等公开工具产出 + 文献坐标 |
| 产胶通路查询序列 | `reference_genomes/tks_rubber_pathway_queries.fasta` | 2026-09-24 | 方案6 通路基因定位 | 文献公开序列 |

### 4. 转录组表达矩阵

见 [`expression/README.md`](expression/README.md)（文件清单、组织/时相维度、基因 ID 对齐关系）。

| 名称 | 获取时间 | 用途 | 来源 |
|---|---|---|---|
| `expression/1-3_lettuce_5tissue_expression_matrix.csv`（5 组织均值，40,267 基因） | 2026-09-22 | 组织特异性敲除适宜性诊断 | 随湿实验数据配套交付 |
| `expression/lettuce_biorep_expression_matrix.csv`（16 文库生物学重复） | 2026-09-22 | 方差检验与差异表达 | 同上 |
| `expression/2-3_TKS_Tiss-Dev-Expression(1).xlsx`（S1–S9 × 5 组织，80 样本） | 2026-09-22 | 产胶发育时相推荐窗口 | 同上 |

### 5. 预训练模型（第三方开源）

| 名称 | 版本 | 用途 | 来源与许可 |
|---|---|---|---|
| DeepSpCas9 | `models/DeepSpCas9/PreTrain-Final-3-5-7-100-70-40-0.001-550-80-60.*`，经 `genet==0.17.2` 调用 | 10 维特征之一（`deepspcas9_score`） | Kim HK et al. *Sci. Adv.* 5, eaax9249 (2019)；开源预训练权重，学术用途 |
| CRISPRon / CRISPRoff | RTH-tools，`requirements-crispron.txt` 锁定 | 10 维特征之一（`crispron_score`） | https://github.com/RTH-tools/crispron ，**GPL / AGPL**；模型权重由 `env/setup_crispron_wsl.sh` 自动获取，不随包发布 |
| Cas-OFFinder | v2.4.1（2021-01-23 构建） | 脱靶位点检索 | https://github.com/snugel/cas-offinder ，MIT；win64 二进制不随包发布 |

---

## 二、数据清洗与预处理记录

Hi-TOM 实测数据的治理全过程见 `results/CHANGELOG_0927.md` 与 `docs/reports/project_progress_report.md`，共修复 **7 类历史问题**：

1. **PAM 错记**：PAM 序列与坐标不匹配行的回溯修正；
2. **坐标偏移**：切割点坐标系统性漂移校正（含 `usr5712_indel_rightside_recompute_0915.csv` 右侧 indel 复算）；
3. **链向整列反转**：负链标注错误导致的整列反向互补修正；
4. **indel 口径低估**：indel 统计窗口边界修正；
5. **多候选竞争未确认样本**：双 gRNA / 多靶点扩增子中设计归属不明的样本剔除（90 行 B 级）；
6. **弱信号身份不明 guide**：36 行无法确认 guide 身份的样本剔除；
7. **编号地雷**：`guide-id` 跨文件编号不一致文件改名 `_DEPRECATED` 留档，杜绝按 ID 静默错配。

**最终训练集口径 `noB879`**：879 行 / 16 基因组 / 35 条 distinct guide，**纯 A 级金标准**（1,368 行原始 → 1,005 行裁决后 → 剔除 90 行 B 级 → 879 行）。

---

## 三、训练 / 验证 / 测试划分方式

| 划分 | 方式 | 参数 | 随机种子 |
|---|---|---|---|
| 外层留出测试 | `sklearn.model_selection.GroupShuffleSplit`，**按 `gene_group` 分组** | `n_splits=1, test_size=0.2` | **`random_state=42`（全队统一）** |
| 内层评估 | LOGO-CV（Leave-One-Gene-Out，留一基因交叉验证） | 16 折（每折留出 1 个基因组） | 确定性，无随机性 |
| 分层评估 | Class A = 低混杂多批核心折（跨 ≥3 批次） | 5 条核心折 | 确定性 |

**划分设计意图**：按基因分组而非按行随机划分，确保同一基因组的多个位点不跨训练/测试集，**从结构上杜绝位点级数据泄漏**。

**随机种子记录**：`random_state=42` 统一固定于 `scripts/06_train_stacking.py`、`13_features_train_full.py`、`14_public_mix_train.py`、`15_train_hierarchical_bb_nob879.py`、`24_model_comparison_nob879.py`、`25_sensitivity_dual_grna_0924.py`；`24_model_comparison_nob879.py` 顶部文档字符串与 `results/model_comparison_nob879_report_0924.md` 记录同一口径。

---

## 四、去重与数据泄漏防控措施

| 风险 | 防控措施 | 证据 |
|---|---|---|
| 同一 guide 跨折泄漏 | `GroupShuffleSplit` + LOGO-CV 均按基因/基因组分组 | `results/folds_hier_bb_nob879_0921.csv` |
| 多候选竞争样本污染 | 剔除 90 行 B 级「多候选竞争未经设计表确认」样本 | `results/CHANGELOG_0927.md` 9.21 第 1、4 款 |
| 弱信号身份不明 guide | 剔除 36 行；剔除后锚定 LOGO 中位 ρ 由 -0.078 → +0.310 | `results/b_anchor_161_0921.csv` |
| 跨文件编号错配 | 编号不一致文件改名 `_DEPRECATED`，禁止按 `guide-id` join | `results/CHANGELOG_0927.md` 9.21 第 6 款 |
| 双 gRNA 标签归属错配 | 读段级切点归属复核 38 行；整体剔除敏感性 ρ 波动仅 -0.0010 | `results/sensitivity_dual_grna_summary_0924.csv`、`results/model_card_hier_bb_nob879_0921.md` §7.1 |
| 公开数据污染生产模型 | 生产模型训练脚本 `15_train_hierarchical_bb_nob879.py` 仅读 `noB879`，公开数据仅在 `14_public_mix_train.py` 独立实验 | `results/transferability_0917.md` |
| 标签口径本底 SNP | 逐块量化披露（SNP-only 占非 WT 0.68%，个别块 13.4%），维持原口径并如实记录 | `results/model_card_hier_bb_nob879_0921.md` §7.2 |

**隐藏评测集**：本项目**未使用、亦不掌握任何未公开隐藏评测集**；全部评估均在上述自有 `noB879` 数据的公开划分口径下完成。

---

## 五、未随包发布数据的获取方式

| 数据 | 不随包原因 | 获取方式 |
|---|---|---|
| `data/raw/`（Hi-TOM 原始 R0/R1 fastq、PCR 检测图、合并源表、筛查序列） | **团队自有未发表实验数据** + 体积大 | 团队共享网盘为权威源；清洗后快照 `hitom/hitom_clean_v1.csv` 等已随包发布，可完整复现清洗链路 |
| CRISPRon 模型权重 | 第三方 GPL/AGPL 模型文件 | `env/setup_crispron_wsl.sh` 自动获取（https://github.com/RTH-tools/crispron ） |
| genet / DeepSpCas9 checkpoint | 第三方模型文件 | `pip install genet==0.17.2` 后首次 predict 自动下载（约 700 KB） |
| Cas-OFFinder win64 二进制 | 第三方二进制 | https://github.com/snugel/cas-offinder Releases 页下载，置于 `tools/cas-offinder/` |
| `results/offtarget_raw_0924.txt`（399 MB 脱靶原始输出） | 体积大、可再生 | `scripts/run_mini_batches.ps1` + `scripts/09_aggregate_offtarget.py` 复现；汇总表 `offtarget_counts_0924.csv` 已随包发布 |

**已随包发布的完整候选库**：`results/lettuce_all_genes_top100_candidates.csv`（452 万行全基因组候选，含全部打分）与标准化最终结果文件 `results/results.csv`（字段规范见 [`../results/RESULTS_SCHEMA.md`](../results/RESULTS_SCHEMA.md)），供筹办方直接复核，无需重跑扫描。
