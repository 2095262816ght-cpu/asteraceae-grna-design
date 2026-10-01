# 教师反馈整理与可行性评估报告

> 反馈来源：2026-09-29 教师新发材料（脱靶详情、gRNA 表达相关指标、基因结构注释、算法透明性、参数设置说明）
> 调研基线：`backend/app/services/offtarget_service.py`、`scoring_service.py`、`cs_pipeline/core/sequence_spec.py`、`frontend/src/components/GenomicTargetMap.tsx`、`CandidateSearchPanel.tsx` 等（详见各条目"现状证据"）
> 结论速览：共 5 大项反馈 → 3 项属于**现有功能不足（需修改/增强）**，2 项属于**新增功能**；全部技术可行，无不可行项，但 2 项需要引入外部计算组件或扩展数据解析，工作量较大。

---

## 总览表

| # | 反馈项 | 性质 | 可行性 | 优先级 | 预估工作量 |
|---|--------|------|--------|--------|-----------|
| 1 | 脱靶只有数量、没有位点详情与 CFD/MIT 评分 | 需修改（功能不完整） | 高 | **P0** | 中（3–5 人日） |
| 2 | 增加 gRNA 二级结构 / 转录效率指标（MFE、poly-T、5'G） | 新增功能 | 中高 | P1 | 中（3–4 人日，MFE 需外部组件） |
| 3 | 基因结构注释（外显子/内含子/TSS/功能域）轨道 | 需修改（图谱信息缺失） | 中高 | P1 | 中大（4–6 人日） |
| 4 | 算法与版本说明透明性 | 需修改（说明不足） | 高 | **P0（成本极低）** | 小（0.5–1 人日） |
| 5 | 关键参数设置详解（PAM/gRNA 长度/评分模型等） | 新增功能（文档+UI 说明） | 高 | P1 | 小（1–2 人日） |

---

## 1. 脱靶分析：从"数量"到"详情"（需修改 · P0 · 可行性高）

### 1.1 教师意见拆解

- 目前"脱靶数 (≤3)"只显示一个数字（如 12），用户无法知道：
  1. 12 个脱靶位点分别在哪里（染色体位置）？是否落在其他基因的编码区？
  2. 各位点错配数分别是多少？（0 mismatch 致命、1 mismatch 高风险、2–3 相对可接受）
  3. 每个位点的脱靶评分（CFD score / MIT score）
- 建议：点击数字弹出抽屉/模态框，列出所有脱靶位点：**染色体位置、错配数、错配碱基位置、所在基因/区域、CFD/MIT 评分**。

### 1.2 现状证据

- 后端 `offtarget_service.py` 已实现 5-mer 种子筛 + Hamming 验证（Cas-OFFinder 口径，PAM=NGG、1–3 错配、正负链），**算法上已经枚举到了每个位点**，但输出层 `OfftargetProfile` 只保留 `exact/mis1/mis2/mis3` 四个累计计数，位点坐标与错配位置在服务内部即被丢弃。
- 导出说明中已自述"不是 MIT/CFD 评分，后续版本可加 CFD 加权"（`export_service.py:137-139`），与教师要求方向一致。
- 前端 `CandidateSearchPanel.tsx:1171-1182` 仅渲染数字；`GenomicTargetMap.tsx:104` tooltip 也只显示计数。单序列打分卡片（`SingleScoringCard.tsx:607-626`）有四档计数，仍无位点坐标。

### 1.3 可行性与方案

**完全可行，且是"低成本高收益"的改进**——脱靶枚举逻辑已存在，核心改动是：

1. **后端**：`OfftargetProfile` 增加 `sites: list[OfftargetSite]` 字段，每条含 `chrom, pos, strand, mismatch_count, mismatch_positions[], pam, spacer_aligned_seq`。注意控制返回上限（如 ≤3 错配位点可能较多，可只回传 top N + 总数）。
2. **CFD 评分**：公开算法（Doench 2016 Nature Medicine 的 CFD 矩阵），有官方 Python 实现（`CFDscore`）与参考权重表（12×12×3 错配类型×位置矩阵），可离线集成，无需联网。MIT 特异性评分（Hsu 2013）同样有公开实现。**建议 CFD 为主、MIT 为辅**（CFD 区分错配位置/类型，信息量更大）。
3. **所在基因/区域注释**：复用 GFF 解析（见第 3 条），对每个脱靶坐标做 overlap 查询，标注"基因间区 / 某基因外显子 / 内含子"。
4. **前端**：数字改为可点击 → Drawer/Modal 表格（位置、链、错配数、错配位点用颜色高亮碱基、CFD 评分、落点区域）；风险分档用颜色（0 mismatch 红、1 橙、2–3 绿）。

### 1.4 风险点

- 位点数量大时（全基因组 3 错配可达数百），需限制返回条数或分页；
- CFD 评分依赖错配类型（ref/alt 碱基对），枚举时需同时记录参考基因组等位碱基——现有流程中参考序列是可得的，无阻碍。

---

## 2. gRNA 二级结构 / 转录效率指标（新增功能 · P1 · 可行性中高）

### 2.1 教师意见拆解

克隆到 U6 启动子表达时，除 GC 含量与效率评分外还需考虑：

| 指标 | 原则 | 教师给定判据 |
|------|------|-------------|
| 二级结构（self-folding） | 发夹结构降低表达/结合效率 | **只算 20nt spacer 自身折叠**（不含骨架序列）；MFE (ΔG) **< −5 kcal/mol 为风险阈值**，优先选 MFE 负值更小（更接近 0 或正值）的候选 |
| Poly-T 终止信号 | U6 遇 TTTT 提前终止转录 | **过滤掉含 TTTT 的 gRNA（硬过滤）** |
| 5' 端碱基偏好 | U6 偏好 G 起始 | 若 5' 为 G 可提高表达（加分项） |

教师明确：MFE 只是参考维度，需与 GC、脱靶、染色质开放状态等综合判断。参考工具：RNAfold（ViennaRNA Web Services），并给出了骨架序列（明确说明**我们采用 spacer-only 方式，不拼骨架**）。

### 2.2 现状证据

- GC、Tm、poly-T 目前**只作为模型特征**（`sequence_spec.py:55-105`，poly_t 系数 −0.1617），**不做硬过滤**；候选枚举唯一过滤是 NGG PAM + 着丝粒。
- ViennaRNA 2.6.4 / RNAfold **已经随项目部署**（`cs_pipeline/tools/win-shims/rnafold/RNAfold_shim.py`、`backend/Dockerfile:23-31`），但目前仅作为 CRISPRon 模型的内部输入，未输出独立 MFE 指标。
- 5' G 偏好：未实现也未预留。

### 2.3 可行性与方案

**可行，且 MFE 计算的成本比看上去低**——RNAfold 已在本地环境中：

1. **MFE 指标**：对每条候选 spacer（20nt）单独调用 RNAfold（`RNAfold --noPS`，只取 ΔG），作为新列"MFE (kcal/mol)"展示，并按教师阈值标注风险（< −5 红色警示）。可批量离线预计算（候选数在数千量级，ViennaRNA 处理毫秒级/条，全量预计算完全可行）。可选：接入本地 RNAfold 已封装为统一接口（现有 `crispron_wsl.py` 的调用方式可复用）。
2. **Poly-T 硬过滤**：枚举阶段直接剔除含 `TTTT` 的 spacer（一行代码），同时保留"被过滤数量"的提示，符合教师"必须避免"的表述。
3. **5' G 偏好**：作为展示列/加分标记（如"G-start ✓"），或作为排序 tie-breaker；**不建议**作为硬过滤（教师表述为"可提高表达"而非"必须"）。
4. **UI**：单序列打分卡与候选表新增"MFE / Poly-T / 5'G"三列或合并为"表达适配度"面板；在排序口径弹窗中说明阈值来源（−5 kcal/mol 荟萃分析阈值）。

### 2.4 风险点

- 教师只给了阈值方向，MFE 阈值来自特定荟萃分析，**建议在 UI 标注"参考阈值，非绝对判据"**（教师原话亦强调需综合判断）；
- 若后续要预测"spacer+scaffold 全长"结构，教师已明确当前不做；
- 不要引入联网 Web 服务（RNAfold 网页版），全部用本地 ViennaRNA，保证离线交付。

---

## 3. 基因结构注释轨道（需修改 · P1 · 可行性中高）

### 3.1 教师意见拆解

染色体图谱目前只有一条蓝色基因条带，缺少：

- 外显子/内含子边界
- 启动子 / TSS 位置
- 蛋白功能域（对 NLR-LRR 类基因，CC/NBS/LRR 结构域位置尤为关键）

建议：图谱中增加基因结构轨道，用不同颜色标注外显子，让用户直观判断 gRNA 是否落在关键功能域内。教师提示：**信息在后缀为 GFF 的文件里**。

### 3.2 现状证据

- `GenomicTargetMap.tsx:177-203` 确实只画基因起止一条横线 + guide 散点，无外显子结构。
- GFF 文件已存在于 `cs_pipeline/data/reference_genomes/`（`1-1_Stem_lettuce_v1.1c.gff`、`2-2_TKS.genome.gff3`、`3-1_LsT2T.annotation.gff3`），但解析时**只取 `gene` 特征行**（`reference_bundle_service.py:100-122`），exon/CDS/mRNA 行被丢弃；TSS 目前用基因边界 ±2kb 启动子近似。
- `is_exon`/`region_type` 字段来自预计算 CSV（`seed.py:294-310`），粒度不足。

### 3.3 可行性与方案

**可行，主要工作在数据解析与前端绘图**：

1. **GFF 解析扩展**：`reference_bundle_service.py` 增加 `mRNA/exon/CDS` 特征解析，按 gene→mRNA→exon 层级组织；TSS 取转录本 5' 端（按链方向），替代现在的 ±2kb 近似。
2. **蛋白功能域**：⚠️ **GFF 中通常不含蛋白结构域注释**（CC/NBS/LRR 需 InterPro/Pfam/HMMER 注释）。分两步走：
   - 短期（可行）：对 NLR 类目标基因（如教师关注的 LRR 基因）离线跑一次注释，把结构域区间作为**旁路注释表**导入——具体最小可行路线见 §3.5；
   - 长期：接入结构域注释流程自动化（全基因组 NLR 普查）。
3. **前端轨道**：`GenomicTargetMap.tsx` 增加基因结构轨道——外显子用实心色块（可按编码/UTR 分色）、内含子细线、TSS 箭头、结构域用第三条轨道色块；gRNA 散点与轨道叠加，hover 显示"gRNA 落在 LRR 结构域内"。
4. **联动第 1 条**：脱靶详情中的"所在基因/区域"也复用这套注释。

### 3.4 风险点

- 不同参考基因组（v1.1c / TKS / LsT2T）GFF 的 feature 层级写法不一致，解析需兼容 GFF2/GFF3 差异；
- 蛋白结构域是本条中**唯一数据来源受限**的部分（GFF 里没有），需单独准备数据，应向教师说明这一点及替代方案。

### 3.5 蛋白功能域注释：最小可行路线（实施细节）

> 前提事实：`cs_pipeline/data/reference_genomes/` 下只有 GFF + 基因组 FASTA，**没有蛋白序列 FASTA**。完整流程为四步：拿蛋白序列 → 注释结构域 → 坐标回映到基因组 → 导入渲染。

```
GFF + 基因组FASTA ──①──> 蛋白序列 ──②──> 结构域(蛋白坐标)
                                              │
                          ③ 坐标换算（蛋白aa位置 → 基因组chr:pos）
                                              ▼
                          domain_annotations.csv ──④──> 前端轨道色块
```

**第 0 步：范围只做目标 NLR 基因（3–5 个）**，不做全基因组普查。演示/回应教师足够，工作量小一个量级；全基因组 NLR 普查列入后续版本。

**第 1 步：准备序列**
- 路线 A（标准）：`gffread 3-1_LsT2T.annotation.gff3 -g 3-1_LsT2T.genome.fa -x cds.fa -y proteins.fa` 提取 CDS 并翻译成蛋白序列，再抽目标基因；
- 路线 B（做 NLR 时更省事）：NLR-Annotator 可直接吃基因组核酸序列，**跳过翻译**，直接输出结构域架构。

**第 2 步：注释工具（三选一）**

| 工具 | 原理 | 优缺点 |
|------|------|--------|
| **NLR-Annotator（推荐）** | 规则/模式库识别 NLR 家族特征 | 输出直接是 CC/TIR/NBS/LRR 及各段位置，正中教师诉求；Java JAR 离线跑、分钟级；仅覆盖 NLR 类 |
| HMMER + Pfam | `hmmsearch` 用 Pfam HMM 模型扫蛋白（NB-ARC=PF00931、TIR=PF01582、LRR 等） | 通用精确可引用；需下载 Pfam-A.hmm（数 GB）；LRR 重复区命中需后处理拼接 |
| InterProScan | 整合多数据库 | 最权威但 Docker 镜像 ~50GB、全基因组数小时，演示场景过重 |

**第 3 步：坐标回映（唯一技术难点）**
结构域工具输出蛋白坐标（"NB-ARC = 蛋白第 120–380 aa"），需换算为基因组坐标：蛋白第 k 个 aa → CDS 第 3k~3k+2 碱基 → 沿转录本 CDS 外显子块逐段累加定位（注意负链反向、CDS phase 偏移）。规避方式：走 NLR-Annotator 核酸路线可直接输出基因组坐标区间。**验证**：随机挑 1–2 个区间把基因组序列反向翻译，核对氨基酸与蛋白坐标一致。

**第 4 步：产出与集成**
产出旁路表 `domain_annotations.csv`：

```csv
gene_id,transcript_id,chrom,start,end,strand,domain_type,domain_name,source
Gene001,Tx001,Chr5,123456,124089,+,NBS,NB-ARC(PF00931),NLR-Annotator
```

集成三处：① 作为参考 bundle 可选附件导入（复用 `ReferenceBundleImporter`/`seed.py` 的预计算 CSV 机制）；② `GenomicTargetMap.tsx` 第三轨道画色块（建议 CC 蓝 / NBS 红 / LRR 绿），gRNA hover 显示"落在 NBS 结构域内（推荐敲除位点）"；③ 与 #1 联动，脱靶详情"所在区域"查此表。

**工作量**（目标基因范围）：序列准备 0.5 人日 + NLR-Annotator 跑通 0.5–1 人日 + 坐标换算核对 1 人日 + 导入渲染 1.5–2 人日 ≈ **3–4 人日**（与外显子/TSS 轨道共享绘制代码；全基因组普查另加 2–3 人日）。

**零成本捷径**：先打开 `cs_pipeline/data/reference_genomes/T2T_Supplemental_Tables_7-9.xlsx` 检查——T2T 文章补充表可能已带 NLR 家族注释表，若有则第 1–3 步全省，直接转 CSV 导入。

---

## 4. 算法与版本说明透明性（需修改 · P0 · 可行性高 · 成本极低）

### 4.1 教师意见拆解

界面有 "Beta-Binomial GLMM (v2.1)" 和 "效率分 (V2.1)"，但用户不知道：

- 效率评分用的是哪个模型？Rule Set 2？DeepCRISPR？还是自研？
- 脱靶搜索用的是哪个参考基因组？关键参数是什么？

### 4.2 现状证据

- 实际算法为**自训练 Stacking 元模型**：DeepSpCas9 + CRISPRon 双模型分 + 10 维序列特征 → 分层选择性 Beta-Binomial GLMM（v2.1 / noB879），有模型卡 `cs_pipeline/results/model_card_hier_bb_nob879_0921.md`。**不是** Rule Set 2/3 或 DeepCRISPR。
- 已有部分透明性工作：排序口径弹窗（`CandidateSearchPanel.tsx:43-92`）、效率分成分悬停、导出 Excel《指标方法说明》sheet、免责声明与 ρ 值标注。
- 缺口：UI 未直接给出**参考基因组版本号**、脱靶算法（Cas-OFFinder 口径、Hamming、1–3 错配、NGG）说明，以及"效率分模型 = 自研 Stacking（DeepSpCas9+CRISPRon）"的一句话出处说明。

### 4.3 可行性与方案

**完全可行，建议最先做**：

1. 在 UI 增加"方法与版本"说明入口（弹窗或设置页），一页讲清：
   - 效率分：自研 Stacking 元模型（DeepSpCas9 + CRISPRon + 10 维序列特征 + Beta-Binomial GLMM v2.1），附模型卡链接与验证指标（ρ=0.464/0.342，保持现有透明标注）；
   - 脱靶：Cas-OFFinder 口径、PAM=NGG、≤3 错配、正负链、**当前参考基因组版本名**（从 reference bundle 动态读取）；
   - 各指标公式（可复用导出 Excel 里已有的《指标方法说明》内容）。
2. 把参考基因组版本号显示在结果页显著位置（数据来自 `ReferenceBundleImporter` 已有元数据）。

---

## 5. 关键参数设置详解（新增功能 · P1 · 可行性高）

### 5.1 教师意见拆解

教师给出了完整的方法学综述（以 SpCas9 为例），要求让用户理解参数设置：

- **核心序列参数**：目标物种基因组、PAM 序列（SpCas9=NGG，Cas12a=TTTV）、gRNA 长度（通常 20nt，部分工具 15–22nt 可调）；
- **编辑效率预测算法**：经典（Doench 2016、Moreno-Mateos）；先进（**Rule Set 3**，Doench 2022，47,000 条 gRNA 训练）；深度学习（DeepHF、CRISPRon）；
- **脱靶风险评估**：MIT 特异性评分、CFD 评分（考虑错配位置和类型）；
- **序列特征过滤**：GC 40%–70%、poly-T 禁忌、二级结构评估。

### 5.2 与现状的对照

| 教师列的参数/算法 | 本项目现状 | 处理建议 |
|---|---|---|
| PAM = NGG、gRNA 20nt | ✅ 已实现（枚举即 NGG、20nt） | 在参数面板明示，允许查看（暂不必开放调整） |
| 物种基因组选择 | ✅ 三种参考基因组 bundle | 显示当前版本名（并入第 4 条） |
| Doench 2016 / Rule Set 2 | 未直接使用 | 说明"本项目采用自研 Stacking，与 Rule Set 2/3 的关系" |
| **Rule Set 3**（2022 最先进） | 未使用 | **可选升级项**：有公开实现，可作为对照分数列或后续模型特征 |
| DeepHF / CRISPRon | CRISPRon ✅ 已是模型成分 | 说明即可 |
| MIT / CFD 评分 | ❌ 未实现 | 并入第 1 条实现 |
| GC 40%–70% 建议区间 | GC 仅作特征 | 展示区间参考线（软提示，不硬过滤） |
| poly-T 过滤 | 仅作特征 | 并入第 2 条改为硬过滤 |
| 二级结构 | 仅作 CRISPRon 内部输入 | 并入第 2 条输出独立 MFE |

### 5.3 可行性与方案

- **主体是文档 + UI 说明工作**（用户手册新增"参数设置详解"章节 + 界面参数面板），可行性高、成本低；
- **Rule Set 3** 若采纳，需注意其官方实现依赖特定 Python 环境（有公开的 `ruleset3` 包/代码），作为对照列集成可行，但**不建议替换现有 v2.1 模型**（已有验证指标与模型卡），只作参考列更稳妥；
- 教师文中的"部分工具允许 15–22nt 可调"属于背景介绍，**不建议**照做（改变 gRNA 长度会影响现有模型有效性）。

---

## 6. 实施建议（排序与依赖）

```
第 1 批（P0，1–2 人日，立即做）
 ├─ #4 算法/版本/参考基因组透明性说明（含模型卡引用）
 └─ #1a 脱靶位点详情：后端输出 sites + 前端抽屉（先用计数分档着色）

第 2 批（P1，约 1 周）
 ├─ #1b CFD 评分集成 + 脱靶位点基因区域注释
 ├─ #2  MFE 列（本地 RNAfold）+ poly-T 硬过滤 + 5'G 标记
 └─ #5  参数设置详解（手册章节 + 参数面板）

第 3 批（P1–P2，视数据准备情况）
 └─ #3  GFF 外显子/内含子/TSS 轨道；NLR 功能域注释（最小路线见 §3.5，约 3–4 人日）
```

**依赖关系**：#1b 的"所在基因/区域"与 #3 共用 GFF 扩展解析，建议合并开发；#2 与 #5 共用"参数/过滤口径"说明文案。

**没有不可行项**。需要向教师说明的两点：
1. 蛋白功能域（CC/NBS/LRR）不在 GFF 文件内，需另跑结构域注释（HMMER/Pfam 或 NLR-Annotator），建议先对重点 NLR 基因离线注释；
2. 效率分模型是自研 Stacking（DeepSpCas9+CRISPRon+GLMM v2.1），不是 Rule Set 2/3；如需对标 Rule Set 3，建议作为对照分数而非替换主模型。

---

## 附：执行状态（2026-09-29 实施完成记录）

五项反馈均已实施。主要落点如下：

**#1 脱靶位点详情 + CFD/MIT 评分（P0）**
- 后端：`offtarget_service.scan_seq20` 输出位点明细（坐标/链/错配数/gRNA 方向错配位置/比对序列/PAM）；`cfd_score.py` 集成 CFD（Doench 2016 官方矩阵，源自 lindayqlin/CFD_score_calculator pickle 转换嵌入）与 MIT/Hsu 2013 单位点 hit score（CRISPOR calcHitScore 口径），guide 级特异性沿用 CRISPOR 公式；数值与官方 doctest 逐位一致（测试 `test_cfd_score.py`）。
- 端点：`GET /api/v1/offtarget/sites`（含风险分档、所在基因区域注释、在靶位点排除、方法口径说明）。
- 前端：候选表"脱靶数 (≤3)"可点击 → 抽屉展示位点表格（风险着色、错配碱基高亮、CFD/MIT、区域/基因）+ 特异性汇总 + 口径全文。
- 真实基因组端到端验证：单 guide 全基因组扫描 66 秒，15 个位点明细/评分/区域注释全部正确。

**#2 表达适配度（poly-T / MFE / 5'G）**
- Poly-T 硬过滤：候选枚举阶段剔除含 TTTT 的 spacer 并计数提示（`gene_candidate_service` + 候选 API `poly_t_filtered_count`）。
- MFE：`expression_fitness_service.spacer_mfe`（仅 20nt spacer 自折叠，不含 scaffold；本地 ViennaRNA），ΔG < −5 kcal/mol 红色警示（参考阈值非绝对判据）；5'G 加分标记。
- 前端：候选表"表达适配"列（MFE/5'G/警示）+ 单序列打分"表达适配度（U6 表达）"面板；导出《指标方法说明》同步补充三条口径。

**#3 基因结构注释轨道（最小可行路线）**
- GFF 解析扩展至 mRNA/exon/CDS 层级，TSS 链感知（`gene_structure_service`）；前端基因结构轨道（外显子色块/内含子线/TSS 箭头）+ 蛋白功能域轨道（CC/TIR/NBS/LRR 分色）。
- 结构域注释：NLR-Annotator v2.1b（官方 jar+motif 数据入库 `cs_pipeline/tools/nlr-annotator`）+ 官方 motif×category 映射（AnnotatorSignatureDefinition）→ 96 个结构域区块（LRR 29 / NBS 26 / TIR 15 / CC 5 / LINKER 21），覆盖 20 个 NLR 基因（其余如实标"暂无功能域注释"）。
- **数据修正**：49 个 NLR demo 基因（LsaT2T* 命名空间）坐标来自外部数据集组装版本，与 LsT2T 参考基因组存在 270–339kb 偏移；已用候选 seq30 全基因组重定位（48/49 成功，1 个候选未命中无法定位），产出 `nlr_gene_loci.csv` 重定位表，gene-structure 端点经该表回退并如实标注坐标来源。

**#4 透明性 / #5 参数详解**
- `GET /api/v1/meta/methods`：效率分模型（自研 Stacking v2.1，非 Rule Set 2/3）、脱靶口径（Cas-OFFinder 式、NGG、≤3 错配、CFD/MIT/CRISPOR 公式）、表达适配度阈值、参考基因组清单、免责声明。
- 前端"方法与版本"常驻按钮 + 弹窗；USER_MANUAL 新增「5. 参数设置详解」章节（6 小节/6 参数表，含模型谱系、MFE −5 阈值、骨架序列不纳入 MFE 等声明）。

**验证汇总**：后端全量回归 65/65 通过（含 CFD 官方数值对齐、脱靶扫描/位点明细、poly-T 过滤、MFE/5'G、GFF 结构/区域判定、重定位回退、脱靶端点、候选 API 新口径等新增/更新用例；一致性测试同步更新至 poly-T 硬过滤新口径）；前端 25/25 测试通过（含抽屉/轨道/面板/弹窗新增用例），tsc 构建无错误；脱靶详情在真实基因组（2.6GB）端到端验证通过。
