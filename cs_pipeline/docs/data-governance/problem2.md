# 当前数据表剩余问题清单（problem 2）

> **检查对象**：`data/1_Hi-results-12-20260913.xlsx`（当前最新版）
> **本文档定位**：**当前时点仍需改动/确认事项的清单**——所有项都不影响训练/已有实验结论。已改正的项移入"二、已改正（留档）"，每次改动后同步更新本文档，使第一节始终是"最新待办"。problem.md 是全过程检查报告（含历史细节），两文档分工：problem.md 记历史，problem2.md 记现状。
> **最近更新：2026-09-16**（strand 列 221 行改正；CATT guide 坐标 1bp 改正；LG02.4820 四行 PAM CCA→ACT 改正；USR-5712 批 61 行 indel 写回为右侧口径真实值；**全量重跑：487 行/14 基因全部纳入训练，见第四节**）。
> **写作约定**：零基础可读。涉及的核心概念在 problem.md 第 4 项的 4.0 节有完整版，这里先做 4 行极简回顾：
>
> 1. DNA 是双链，同一位点从正链/负链看是两条不同的字符串（互为反向互补）；
> 2. Cas9 切割的硬规则：guide 的 20nt 旁边必须紧跟 NGG 模式的 3bp（PAM），否则不切；
> 3. 切割点固定在 PAM 上游约 3bp，切口处的插入/缺失（indel）就是"编辑成功"的信号；
> 4. 本表 indel_pct 的统一口径 = 切割侧非 WT reads / 总 reads（多数批次切割点在输出表左侧）。

**总体结论**：23 条 distinct guide 逐条回 TKS 基因组比对，序列、坐标、链向、PAM 已全部自洽（最后的例外——LG02.4820 第二位点 4 行 PAM——已于 2026-09-16 改正为基因组实测值 ACT，见二.C），其余待办均为"确认/决策"性质而非"改错"。核查脚本：仓库根 `_check_all_strands.py`、`_check_strand_convention.py`、`_check_remaining.py`。

---

## 一、仍需改动 / 待确认（当前清单）

### 1. 多拷贝 guide：一条 guide 同时命中两个基因拷贝（归属记法待确认）

- `CGTAAGGATTGCTGCTGAGA`+AGG 和 `TGTTCATCGGTGATCTCGAT`+AGG 在基因组里各有 **2 个完全相同的命中**（LG01.6995 与 LG01.6999 是一对序列几乎完全相同的同源拷贝）。
- 后果：从测序 reads 无法区分编辑发生在哪个拷贝上（USR-8145 批用 CPT1/CPT2 两个 amplicon 分别扩增，实际上做了区分；但归属记法本身依赖于 amplicon 设计的先验知识）。原"LG02.6246"的 2 行（TKS_0356/0358）暂记到 6995 名下，属待确认的记法（详见 problem.md 第 5 项）。
- 对训练的影响可忽略：特征只来自 guide 序列本身，两拷贝高度同源，LOGO-CV 分组时本就应视为一家。

### 2. 两批已改正的高效数据（93 行）尚未进训练集　`[已解决（2026-09-16）：全量重跑已纳入，见四]`

- **5712 批**（61 行）：9.15 已把序列更正为真实 guide `GAAAATGTCAGGATGCCTGA`+AGG；9.16 已把 indel_pct 写回为切割点侧（右列）口径真实值（中位数 0.0123→1.0，见二.D）。
- **6995/6999 批**（32 行）：9.15 已把移位 5bp 的错误窗口更正为 `CGTAAGGATTGCTGCTGAGA`+AGG，更正后的 23nt 在基因组/CDS 中均可正常映射。
- **2026-09-16 已连同其余未进训练的批次（USR-23709/25902/26162）一起做全量重跑**（487 行 / 14 基因 / 13 分组），脚本与产物见第四节；两批 oligo 终核（见第 4 项）仍建议补做，如有出入以合成记录为准再调整。

### 3. 数据治理小项（维持 problem.md 结论，此处仅列要点）

| 问题 | 要点 | 影响 |
|---|---|---|
| 样本信息丢失 | 单样本号已并入测序订单号，无法回溯"每行=哪株植株" | 仅影响数据治理与将来按样本剔除/降权 |
| `efficiency-norm` 全空 | 491 行全空，需业务方提供归一化方法 | 训练用 indel_pct 原值，无影响 |
| `rep` 列混杂 | 298 行数字 + 193 行"暂不填" | 未做重复间聚合，无影响 |
| 第一列 `列名` 全空 | 无效列 | 视觉冗余 |
| Sheet2~5 无表头/冗余 | Sheet3 全为同一对坐标、Sheet4/5 与 Sheet1 行数对不上 | 下游只读 Sheet1，无影响；注意 Sheet2 是 LG07.3296 等位点的注释来源（曾帮 problem.md 第 2 项定案），不要删 |

**版本比对记录（2026-09-16）**：同学改版 `data/1_Hi-results-12-20260913tclassmate'srevisedversion.xlsx` 与本地最新版逐单元格比对：全部数据列（序列/PAM/坐标/strand/indel_pct）与 Sheet2~5 **完全一致**（含 9-15 两项序列更正与 9-16 的 strand/坐标改正），唯一差异是 5712 批 61 行 + 6995/6999 批 32 行的**更正备注被清空**（93 个单元格）。**处理决定（2026-09-16）**：本地版是同学版的严格超集（数据相同 + 备注溯源更全），**无需合并，继续以 `data/1_Hi-results-12-20260913.xlsx` 为准**；同学版仅作留存，不再改动。

### 4. 唯一欠缺的外部证据：oligo 合成/设计记录终核

两批已更正数据的 oligo 合成/设计记录（5712 的 rfSP3、6995/6999 的 CPT 靶点）：

- 现有证据（reads 切割点定位 + Sheet2 记录 + 同 guide 他批记录）已足以支撑更正，置信度很高；
- 但 oligo 订单不在 `data/` 内，100% 定论需向实验同学索取合成记录逐字核对；
- 如有出入，以合成记录为准再调整（各次更正前的 xlsx 备份均在 `data/` 下，可随时回滚）。
- **状态更新（2026-09-16）：oligo 记录暂无法获取，按现有证据链定稿，不阻塞任何下游工作。** oligo 终核能补的只是"当初为何填错"的叙事，改变不了"实际被测序列"的事实（5712 的 reads 切割点定位是铁证：记录位点 61 个样本零编辑、全部 indel 落在更正后位点）。若日后拿到合成记录且有出入，再按上一条回滚调整。

---

## 二、已改正（留档备查）

### A. strand 列整列填充错误　`[已改正（2026-09-16）：221 行 - → +]`

- **约定**：strand = guide 所在链——seq-20 逐字命中基因组 fasta（正链）记 `+`；seq-20 的反向互补命中记 `-`。
- **基因组证据判定**：旧表全表 491 行均为 `-`，但实测 23 条 guide 为 12 条正链（221 行）/ 11 条负链（270 行），"gRNA 全设计在反义链"的解释被排除，**坐实为整列填充错误**。三方互证：正链 guide 所属的 8 个基因（LG01.555/557/8265、LG02.4013/4820、LG03.2345、LG04.2802、LG05.2111）恰好就是 Sheet2 标 `+` 的 8 个，负链 guide 所属 6 个基因对应 Sheet2 的 `-`——Sheet2、Sheet1 序列、基因组三方自洽，唯一对不上的就是旧的 strand 列。
- **已改正**：221 行 `-` → `+`（负链 270 行本就正确，未动）。修复脚本：仓库根 `_fix_strand.py`（逐行回基因组判定链向，非按名单硬改）；备份 `data/1_Hi-results-12-20260913_backup_20260916_080357_prestrandfix.xlsx`；改正后读回验证 `+` 221 行 / `-` 270 行，与附录表"链"列一致。
- 对训练无影响（无脚本读该列）；改正后做位点级分析（切割坐标、脱靶评估）可直接使用此列。

### B. CATT guide（LG07.3296，13 行）坐标整体差 1bp　`[已改正（2026-09-16）]`

- 记录坐标 LG07:109029137-109029157，基因组实测其反向互补命中在 **109029136**——整体偏移 1bp。其余 22 条 guide 在同一坐标口径下全部精确吻合，排除"0 基/1 基口径差异"的解释，属录入偏移。
- 序列和 PAM 本身完全正确（负链，AGG 吻合），01 管线按序列比对自行推断坐标、不读这两列，对训练无影响。
- **已改正**：13 行 start/end 改为 109029136-109029156；修复脚本 `_fix_catt_coord.py`；备份 `data/1_Hi-results-12-20260913_backup_20260916_080922_precattcoordfix.xlsx`。

### C. LG02.4820 第二位点 4 行 PAM 记录错误　`[已改正（2026-09-16）：CCA → ACT]`

- **现象**：TKS_0260/0261/0262/0264 四行，guide `AACATGGTTCGAGTTCAAGA`、PAM 记 `CCA`；基因组正链 147965966-985 逐字命中，但下游 3bp 实为 `ACT`——既非 CCA 也不合 NGG 规则。已排除窗口移位（±8bp 内无 NGG）；记录的 CCA 实为 guide **上游** 3bp（填表时从另一端抄错）。
- **ACT 经双重独立来源确认**：参考基因组组装（`2-1_TKS.genome.fasta`）与实验原始 reads（USR-25902 交付文件，含该 guide 的 reads 共 10 处下游 3bp 全为 ACT、无一处 CCA）一致，可排除"参考基因组组装错误"。
- **实测与"无 NGG → 切不动"自洽**：4 行 indel_pct = 0 / 0.0473 / 0 / 0（USR-25902 批），唯一非零值与该位点已知天然 SNP（T→C，见 problem.md"一、已解决 8"注）背景一致——即实测基本无编辑活性，属无效/低效设计，**不是实验事故**。
- **已改正**：4 行 pam 由 `CCA` 改为基因组实测值 `ACT`（如实记录该无效位点，不删行——indel≈0 是真实测序结果，留作阴性对照），备注列追加说明。修复脚本 `_fix_pam_act.py`（先经基因组验证再改）；备份 `data/1_Hi-results-12-20260913_backup_20260916_220526_prepamactfix.xlsx`。
- **对本项目的影响**：**无**。00 合并脚本用 `^[ACGT]GG$` 正则只收 NGG PAM 的行，这 4 行（改前 CCA、改后 ACT 均非 NGG）始终被自动剔除，从未进入训练集。
- **残留待确认（不阻塞）**：可顺口问实验同学该位点是否故意选用非 NGG PAM 设计；答案不影响数据与模型。

### D. USR-5712 批 61 行 indel 左侧口径低估值　`[已写回（2026-09-16）：改为切割点侧（右列）口径真实值]`

- **背景**：统一口径"左侧非WT"隐含前提——参考序列按使切割点落在左侧的方向提交。USR-5712 批参考按负链提交（事实链见 problem.md 第 4 项），切割信号落在输出表右列，左侧口径算出的 indel 被系统性低估。
- **行序=块序对应关系验证**：61 行按表内顺序与重算表块 001–084 顺序对照，左口径 **60/61 逐行吻合**（倒序仅 15/61，排除）；唯一例外 TKS_0095（原值 0.1117 与任何块的左口径都对不上，属原始记录异常），写回后异常随之消解。
- **已写回**：61 行 indel_pct 由左侧低估口径改为右侧（切割点侧）口径重算值（来源 `data/hitom/usr5712_indel_rightside_recompute_0915.csv`），每行备注注明口径变更与原值；写回后该批中位数 0.0123→**1.0**、均值 0.053→0.778。修复脚本 `_fix_5712_indel_writeback.py`；备份 `data/1_Hi-results-12-20260913_backup_20260916_222255_pre5712indelwb.xlsx`。
- **⚠️ 口径混合提示**：写回后全表 indel_pct 为**混合口径**——仅这 61 行是"切割点侧（右）"口径，其余 430 行仍是"左侧"口径。做全表统计/训练时以备注列和本条为准，勿不知情混用。
- 与训练的关系：该批目前不在训练集内；纳入训练前的硬性前提（indel 写回）至此已完成，余下前提是 oligo 终核（一.4）与重跑 01→06（一.2）。

---

## 三、分析时注意（非改动项）

### indel 口径的"方向性前提"是脆弱点（5712 事件的系统性教训）

- 统一口径"左侧非WT"隐含前提：参考序列按使切割点落在左侧的方向提交。5712 批曾因此中招（indel 被系统性低估），**已于 2026-09-16 写回为切割点侧（右列）口径真实值（见二.D）**——注意全表 indel_pct 现为混合口径，仅 5712 的 61 行是右侧口径。
- **其他批次已核查无恙**：USR-5713（左列可见 guide+CGG）、USR-4411（同左）、USR-8145（切割点恰在左右列接缝处，两列都记到变异，indel=1.0 已用原始 reads 核实）、USR-23709/25902（口径经 11 个已知值交叉验证）。即该风险目前只在 5712 兑现。
- 建议：以后每收到一批新 Hi-TOM 结果，先检查"guide+NGG 是否出现在左列"再套统一口径——一步字符串搜索即可，脚本可参考 `_check_5712_strand.py`。

### 批次效应：同一条 guide 在不同批次编辑率差异极大

- `GGCGTTAGATTGACAGAAGA`（LG05.2725，140 行）同时出现在 USR-5713（indel 0~0.52）和 USR-4411（0~0.09）两批，水平差数倍。
- 这不是记录错误（两批数值均已经原始文件抽查核实），而是真实的批次差异（不同代次/不同植株群体）。**训练时需注意**：模型学到的是"序列→效率"，同序列两个差异巨大的标签会互相拉扯；如做批次间比较或归一化，需先把批次作为协变量处理。

---

## 附：全量核查结果表（23 条 distinct guide，2026-09-16 状态）

| gene | seq-20 | PAM | 链 | 坐标核对 | 拷贝数 | 表内行数 |
|---|---|---|---|---|---|---|
| LG01.555 | GATTATGCTAAGGACAAGAG | TGG | + | ✅ | 唯一 | 1 |
| LG01.555 | TGGTCCGCTGAAACCTCACG | TGG | + | ✅ | 唯一 | 19 |
| LG01.557 | CGTCCTACCTCCGATCGTGA | AGG | + | ✅ | 唯一 | 19 |
| LG01.6995 | CGTAAGGATTGCTGCTGAGA | AGG | - | ✅ | 2（含6999） | 18 |
| LG01.6995 | TGTTCATCGGTGATCTCGAT | AGG | - | ✅ | 2（含6999） | 1 |
| LG01.6999 | CGTAAGGATTGCTGCTGAGA | AGG | - | ✅（第二拷贝） | 2 | 16 |
| LG01.8265 | CCAATCGCGAGAAAAAAAAG | TGG | + | ✅ | 唯一 | 36 |
| LG01.8265 | GGACAATTTCAAATTAGGAG | AGG | + | ✅ | 唯一 | 2 |
| LG02.4013 | AAGTCTCGATCTAATTTACA | TGG | + | ✅ | 唯一 | 29 |
| LG02.4013 | GAGAGGGTGGACGTCCAAAC | AGG | + | ✅ | 唯一 | 28 |
| LG02.4820 | AACATGGTTCGAGTTCAAGA | ACT | + | ✅（PAM 2026-09-16 由 CCA 改正为基因组实测 ACT，见二.C） | 唯一 | 4 |
| LG02.4820 | TTCAAGTTCTAAGTAATCCT | CGG | + | ✅ | 唯一 | 6 |
| LG03.2345 | TTATTTTTCATGTTCTAATT | TGG | + | ✅ | 唯一 | 11 |
| LG03.4470 | AACTTTCAATTTGATCGTCT | TGG | - | ✅ | 唯一 | 3 |
| LG04.2802 | AGCCGCCGAGAAAATGATGC | AGG | + | ✅ | 唯一 | 58 |
| LG05.2111 | GCGATTCTAAATCTCCCTCA | AGG | + | ✅ | 唯一 | 8 |
| LG05.2725 | GGCGTTAGATTGACAGAAGA | CGG | - | ✅ | 唯一 | 140 |
| LG07.3296 | CATTACCAAAATAAAACAGG | AGG | - | ✅（2026-09-16 已改正 1bp 偏移） | 唯一 | 13 |
| LG07.3296 | GAAAATGTCAGGATGCCTGA | AGG | - | ✅ | 唯一 | 61 |
| LG07.3933 | AGAGTCGCCCCTGTTGATTC | TGG | - | ✅ | 唯一 | 2 |
| LG07.3933 | CCCCTGTTGATTCTGGATTC | TGG | - | ✅ | 唯一 | 5 |
| LG07.3933 | GACACAATTGTTGCAGATTT | TGG | - | ✅ | 唯一 | 3 |
| LG07.3933 | TATTCGCCAGGTGGACGATC | AGG | - | ✅ | 唯一 | 8 |

> 注 1：LG01.6999 的 CGTA guide 坐标核对标 ✅——其序列同时命中两个拷贝，记录坐标 165502832 与第二拷贝的实测位置精确一致；表中"多拷贝"指序列层面无法区分编辑归属（见一.1）。
>
> 注 2（2026-09-16）：Sheet1 的 strand 列已按上表"链"列改正（221 行 `-` → `+`），现与此表一致；CATT guide 坐标亦已改正。

---

## 四、全量重跑记录（2026-09-16，全数据纳入训练）

**动机**：93 行已改正高效数据（5712×61 + 6995/6999×32）此前未进训练集；本次以改正版 xlsx 为唯一事实源做全量重跑，连同此前从未进训练的 USR-23709/25902/26162 批一并纳入。

**管线与产物**（9.x 冻结产物一律未动，新产物带 `_full_0916` 后缀）：

| 步骤 | 脚本 | 产物 |
|---|---|---|
| 00+01 等价：xlsx→clean 表→seq30 | `scripts/10_rebuild_full_dataset.py` | `data/hitom/hitom_clean_full_0916.csv`（487 行，NGG 过滤剔除 4 行 ACT）、`data/hitom/hitom_seq30_full_0916.csv`（487/487 全命中：415 CDS + 72 基因组坐标回退） |
| 02 等价：DeepSpCas9 | `scripts/11_score_deepspcas9_full.py` | `results/scores_deepspcas9_full_0916.csv` |
| 03 等价：CRISPRon（WSL） | `scripts/12_score_crispron_full.py` | `results/scores_crispron_full_0916.csv` |
| 05+06 等价：合并→特征→训练 | `scripts/13_features_train_full.py` | `results/feature_matrix_full_0916.csv`、`model_comparison_full_0916.csv`、`logo_cv_full_0916.csv`、`meta_model_ridge_full_0916.joblib`、`logo_cv_box_full_0916.png` |

**与旧管线的三点差异（有意为之）**：

1. **CDS 未命中回退基因组坐标**：5712 的 GAAA guide 在内含子（CDS 搜不到），LG03.2345 同；这 72 行按表内坐标从基因组取 30nt 上下文（坐标已经基因组验证，自校验断言通过）。
2. **同源拷贝合并分组**：LG01.6995/6999 合并为同一 LOGO/划分分组（防同源泄漏，见一.1）。
3. **Ridge solver 显式指定 `svd`**：crispr 环境的 scipy 1.15.2 cholesky 路径（`scipy.linalg.solve`/dposv）在本机硬崩（exit 127 无 traceback），默认 `solver="auto"` 会中招；svd 与 cholesky 的岭回归解数值等价。**当日已将 scipy 降级至 1.14.1 并验证修复**（cholesky 路径与 Ridge 默认 solver 均恢复，冻结脚本 `06_train_stacking.py` 可正常运行；sklearn/TF/genet 未受影响）。

**附带发现（两点，已核实）**：

- **训练标签 efficiency_norm 实际 = indel_pct × 100**：scores_merged_0911 中 260/260 行逐值相等（尽管 04 脚本注释称是"F1 表自带的批次内百分位"）。xlsx 的 efficiency-norm 列全空不影响重跑——按此实证约定重建即可。
- **CRISPRon WSL 路径已修**：`env/run_crispron_wsl.sh` 仍指向仓库改版前的 `data/crispron_io/`，已改为 `data/hitom/crispron_io/`（旧脚本 03 此前因此无法运行）。

**结果（487 行 / 14 基因 / 13 分组）vs 旧冻结版（260 行 / 7 基因）**：

| 指标 | 旧（0919 冻结） | 全量（0916） |
|---|---|---|
| 测试集 Spearman ρ（Stacking） | -0.344 | -0.676 |
| LOGO-CV 中位 ρ（Stacking） | -0.225 | **+0.414** |

- LOGO-CV 有定义的 7 折：LG07.3296 0.68、LG02.4013 0.65、LG07.3933 0.42、LG02.4820 0.41、LG01.8265 0.22、LG01.6995/6999 0.08、LG01.555 -0.32。旧版仅 2 折有定义且均为负——**全量数据的泛化能力明显改善，但离达标线 ρ≥0.5 仍有距离**。
- 测试集 ρ 为负的解读：外层 8:2 只留出 3 个基因（LG01.555、LG05.2111、LG07.3296），其中 LG05.2111 只有 1 条 guide（组内无排序信号）、LG01.555 标签呈开关式（0 与 100 两极）；单测试折在 13 个基因上噪声极大，应以 LOGO-CV 为准。
- 结构性限制：14 个基因中 8 个只有 1 条 distinct guide——特征全部由序列派生，单 guide 基因内所有行特征向量相同，LOGO 折内无法定义排序（6 折 rho 因而为 NaN）。**要进一步提升，瓶颈在 guide 多样性而非行数**：需要更多不同序列的 guide，而不是同一 guide 的更多重复。

**下游交付物同步（2026-09-16 当晚完成）**：

- **demo 候选重打分**：`demo/rescore_demo_full_0916.py` 对 19,839 条 demo 候选用**真实** DeepSpCas9 + **真实** CRISPRon（WSL）+ 全量模型重打，新列 `efficiency_score_full_0916` 写回 `demo/app_data.csv`（改前备份 `demo/app_data.backup_20260916_pre_rescore.csv`）。这修复了旧 `efficiency_score` 列"推理期用近似公式伪造 CRISPRon 特征"的问题（CHANGELOG_0927 第 4/5 条的 ⚠️ 对新列不适用）。`app/app.py` 已优先展示新列，`scripts/predict.py` 默认模型已切全量版（其运行时 crispron 近似在 docstring 显著标注）。
- **已知病态（诚实声明）**：新模型仍未达 ρ≥0.5；样本内 guide 级（23 条）回判 ρ 仅 0.402；deepspcas9 特征系数为负（共线性 artifact）；5712 的 GAAA guide 样本内被误判为 0 分（其真实 indel≈100——该 guide 为内含子位点，两公开模型在其上下文上打分模式与训练分布差异大）。demo 新效率分可供内部参考排序，对外演示的免责立场维持 CHANGELOG 原判。
