# 答辩学习 04：多组学时空决策与脱靶评估

> **用途**：应对"多组学体现在哪？表达数据真的用上了吗？脱靶怎么算？"一类追问。
> **深挖入口**：`docs/reports/multiomics_five_schemes_implementation_report_0924.md`（六方案实测）、`docs/plans/multiomics_implementation_plan.md`（蓝图）、`core/ranking_semantics.py`（公式单点）、`results/ablation_expression_report_0923.md`（消融）、`results/offtarget_runlog_0924.md`。

---

## 1. 表达数据（三种表，先说清来源）

| 表 | 物种 | 规模 | 口径 |
|---|---|---|---|
| `1-3_lettuce_5tissue_expression_matrix.csv` | 莴苣 | 40,267 基因 × 5 组织（根/茎/叶/花/种子） | 均值表达（TPM），ID 为 `LSA*`，与 v1.1c GFF 对齐 |
| `lettuce_biorep_expression_matrix.csv` | 莴苣 | 40,267 × **16 个测序文库（生物学重复）** | Root 2 / Stem 5 / Leaf 7 / Flower 1 / Seed 1，供方差与 CV 计算 |
| `2-3_TKS_Tiss-Dev-Expression.xlsx` | 橡胶草 | 36,239 基因 × **S1–S9 发育时相** × 5 组织 | 根/叶全程、胶乳 S4–S9、花/花葶 S6，各 3 重复 |

派生特征：E = log2(TPM+1)；组织特异性 τ = Σ(1−TPM_t/max)/(T−1) ∈ [0,1]；重复间 CV = σ/(μ+ε)。

---

## 2. 六大应用方案（全景表——"多组学体现在哪"的标准答案）

| 方案 | 内容 | 状态 | 实测结论 |
|---|---|---|---|
| 1 | Demo 五组织表达看板 + 表型预警 | ✅ | TPM<0.5 弱表型警示 / ≥10 适宜靶向；14 个无表达注释基因**如实标注不编造** |
| 2 | 表达量对编辑效率的消融 | ✅ **阴性** | 基因级 ρ 全不显著（n=16）；嵌套 GLMM 表达系数自助 CI **全部跨 0** → 无表达效应 |
| 3 | 组织特异优先指数重排 | ✅ | Leaf top50 与纯效率分 top50 **仅重叠 1 条**——重排真实改变推荐 |
| 4 | 多组学重训冲 ρ≥0.50 | ⛔ 正式降级 | 双独立理由（物种错配 + 方案 2 已证伪 RNA 路径），ATAC 特征改投方案 3/5 |
| 5 | 组织功能性脱靶危害 | ✅ 轻量版 | 面板内 10,120 位点危害分交付；完整版 liftover spike 4 判据过 1，否证搁置 |
| 6 | 橡胶草产胶发育时相窗口 | ✅ | REF/SRPP/CPT 三家族统一推荐 **S4** |

**阴性结果也是结论**（答辩加分点）：方案 2 排除了"转录活性是主要混杂"的替代解释；方案 4/5 的降级均有预注册判据与实验否证，不是烂尾。

---

## 3. LSA↔T2T 跨版本注释映射（crosswalk）

**问题**：表达矩阵（v1.1c，`LSA*`）与 T2T 基因组（`LsT2T*` / demo 交付表 `LsaT2T*`）是**四套互不对应的 ID 命名空间**，同号不同基因、坐标偏移 −25kb~−339kb，仓库无现成映射表。

**解法——分层混合映射（不硬猜）**：基因座级锚点投票（40-mer，提供窗口提速）→ guide 级精配（20-mer，≤2 错配 + 基因级投票）→ scaffold 第三层救回 → 第四层如实标 `unmappable`。

**tier 语义**：
- `mapped`：同染色体共线 + 偏移一致 ≥60% + 主映射票 ≥50%；
- `mapped_cluster`：串联重复基因簇（票分裂但簇覆盖 ≥50%）；
- `mapped_scaffold`：证据落在未挂载 scaffold（≥3 票共识）；
- `unmappable`：解析占比 <20% 或票/簇覆盖不足——**不编造映射、不编造 TPM**。

**规模数字**：

| 口径 | 结果 |
|---|---|
| demo 49 NLR 基因 | 35/49 = 71.4% 映射成功（tier1:11 / 簇:21 / scaffold:3 / 缺失:14） |
| 全基因组 45,981 基因 | tier1 60.2% / 簇 15.8% / scaffold 2.0% / 诚实缺失 22.0%；可映射 78.0%（35,783 个取得真实 TPM） |

"不硬猜"纪律有**回归测试固化**（`tests/test_pipeline_engine.py` 断言 tier4 必须无 lsa_primary、票占比阈值等）。工程教训：命中数爆炸曾致 660M 行 OOM，修复为 code 级限流 + 最优命中一次选择。

---

## 4. 排序公式（`core/ranking_semantics.py` 单点定义，答辩要能默写）

### 方案 3：组织优先指数

$$\text{PriorityScore} = 0.50 \cdot \text{Percentile}(\text{EffScore}) - 0.25 \cdot \text{Penalty}(\text{OffTarget}) + 0.25 \cdot S(E_t)$$

- $S(E) = \text{sigmoid}(\log_2(\text{TPM}+1) - 2.0)$；无表达证据（unmappable）→ 记 0（**不加分不倒扣**）；
- $\text{Penalty} = \min\!\left(1,\ \frac{1.0\cdot exact + 0.5\cdot mis1 + 0.2\cdot mis2 + 0.05\cdot mis3}{10}\right)$。

### 表观折中变体（ATAC 加权）

$$\text{PriorityScore}_{ATAC} = 0.45\cdot EffPct - 0.25\cdot Penalty + 0.20\cdot S(E) + 0.10\cdot Atac$$

ATAC 可及性分：峰内 0.6+0.4·min(1, FC/10)；峰近端（≤5kb）0.3·(1−dist/5000)；其余 0。

### 方案 5：功能性脱靶危害

$$\text{Hazard}_t(g) = \sum_k \omega(mis_k) \times w_t(\text{gene}(k)), \quad \omega = \{0{:}10,\ 1{:}3,\ 2{:}1,\ 3{:}0.2\}$$
$$w_t = 1 + 0.5\cdot\log_2(\text{TPM}_t + 1)\ \text{（命中基因不可映射时取背景基线 0.1）}$$

含义：gRNA 对面板内关键功能基因座的误伤风险，按错配物理接触衰减 × 非靶标组织表达量加权。

**单点定义的意义**：公式、权重、公式文案（`*_formula_text()`）只有一处，科研轨（scripts 21/22）、推荐引擎、后端、导出方法学共用——**数字不许漂移**，被问"权重怎么定的"时答案永远一致。

---

## 5. 方案 6：橡胶草产胶发育时相窗口（S4）

- **背景**：天然橡胶生物合成通路三家族 **REF**（橡胶延伸因子）/ **SRPP**（小橡胶粒子蛋白）/ **CPT/HRT**（顺式聚异戊二烯转移酶）；TKS 注释无功能注解，靠同源识别（EBI dbfetch 拉 9 条橡胶树参考蛋白 → 5-mer 词预筛 + Smith-Waterman 验证，identity≥0.30 / coverage≥0.50）。
- **成员**：SRPP 8 个（含 LG01.550–554 串联簇）、REF 2 个、CPT 4 个（含 Hi-TOM 训练集同源对 LG01.6995/6999）。
- **动力学结论**（`results/tks_developmental_window_0923.csv`）：

| 家族 | 胶乳峰值 | 根爆发期 | 推荐窗口 |
|---|---|---|---|
| REF | 6,225 TPM（S4，首采样即峰后单调降） | S6 | **S4** |
| SRPP | 2,139 TPM（S5） | S4 | **S4** |
| CPT | 1,467 TPM（S4） | S4 | **S4** |

→ 三家族统一推荐 **S4 幼苗期（胶乳初生期）** 启动 Cas9 诱导；如实标注"S4 之前的胶乳上升过程无采样、不可观测"。

---

## 6. 脱靶评估（Cas-OFFinder 体系）

### 6.1 全局脱靶扫描（demo 范围）

- **工具**：Cas-OFFinder v2.4.1（win64，GPU `G0`）；输入 49 个 NLR 基因全部候选 **19,839 条 guide**，模式 `NNNNNNNNNNNNNNNNNNNNNGG`，**错配 ≤3**，参考 = 莴苣 T2T 9 染色体。
- **运行**：40 分批 × 约 500 条/批（`run_mini_batches.ps1`）合并；CPU 等价命令一行可复现。
- **冻结规模**：**6,088,827 个命中位点**；mis3=0 的 guide 782 条；**mis3 脱靶中位数 16 / 均值 326.7 / 最大 132,951**。
- **汇总表** `offtarget_counts_0924.csv`：`exact_match_count` + mis1/2/3 **累计口径**（mis2 含 mis1），19,839 行，经 `prepare_demo_data.py` 并入 demo 数据。

### 6.2 位点级脱靶详情（教师反馈 #1 落地）

- `GET /api/v1/offtarget/sites`：5-mer 种子筛（鸽笼原理：≤3 错配 ⇒ 4 块 5-mer 必有一块精配）+ Hamming 验证，输出坐标/链/错配数/错配位置/比对序列/PAM；
- 评分双口径：**CFD**（Doench 2016 官方矩阵）+ **MIT/Hsu 2013**（CRISPOR calcHitScore 口径），guide 级特异性沿用 CRISPOR 公式，与官方 doctest 逐位一致；真实基因组单 guide 全基因组扫描 66 秒端到端验证。

### 6.3 着丝粒过滤

`data/lettuce/centromere_regions.bed`（出自莴苣 T2T 论文补充表）标记 `in_centromere`；引擎默认 `hide_centromere=True` 剔除；修复 Chr1 vs Chr01 命名规范化 bug 后核对 49 个 demo 基因候选与着丝粒区间零交集。

### 6.4 功能性脱靶危害实测（方案 5 轻量版）

面板内位点合计 **10,120**（mis 阶梯 1164/2601/2909/3446）；14,575 条 guide 危害为 0；P95 = 6.4、max = 166.9（`Lsat_10968423` 带 13 个完美旁系位点）。

---

## 7. 基因结构注释与区域过滤（教师反馈 #3 落地）

- **区域分类**：`exon / intron / promoter / intergenic`；启动子 = TSS 上游**链感知** 2kb 窗口；判定规则单点定义（gene-structure 模块）。
- **扫描侧**：exon 经 `exon.Parent→mRNA→gene` 两层映射（236,163 个 exon 全部成功）；候选区间 = 启动子 + 全部外显子。
- **NLR 功能域**：NLR-Annotator v2.1b → **96 个结构域区块**（LRR 29 / NBS 26 / TIR 15 / CC 5 / LINKER 21）覆盖 20 个 NLR 基因，其余如实标"暂无功能域注释"。
- **数据修正**：49 个 NLR demo 基因坐标与本地 T2T 参考存在 270–339kb 偏移，用候选 seq30 全基因组重定位（48/49 成功），产出回退表并如实标注坐标来源。
- **过滤优先级**：`region_type` 过滤优先于 `exon_only`（`CandidateQuery` 单点定义）。

---

## 8. 防雷与口径提醒（本板块）

1. **效率百分位口径两说**：scripts/21 与 0924 报告为"全部 19,839 候选内百分位"（跨基因可比）；`ranking_semantics.py` 文案为"同基因内百分位"——引用时明确所用口径（推荐表述：同基因内相对排序）。
2. 计划文档里"方案 5 完整版（面板外管家基因危害）"与"方案 4 的 32 维特征"均为**未交付**的立项参考，勿当已实现。
3. `results/offtarget_raw_0924.txt`（399MB 原始输出）与 `centromere_regions.bed` 不随包，数字以冻结日志为准。
4. 表达证据缺失 ≠ 转录静默：UI 显示"表达证据缺失"（unmappable），两者生物学含义不同，别混说。
5. 教师反馈五项（脱靶详情、表达适配度 MFE/poly-T/5'G、基因结构轨道、算法透明性、参数详解）已全部实施，后端 65/65、前端 25/25 测试通过——可作为"响应迭代能力"的证据。
