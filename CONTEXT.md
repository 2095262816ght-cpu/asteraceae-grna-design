# 菊科 CRISPR/Cas9 基因编辑设计管线 — 领域术语表 (CONTEXT.md)

本文件定义菊科菊苣族（莴苣、橡胶草）CRISPR/Cas9 gRNA 设计、效率预测与多组学时空决策管线的统一领域语言。所有模块、接缝、接口与测试均遵循本表命名。

---

## 1. 序列与靶位点 (Sequence & Target Site)

- **靶位点序列 (`Target Site` / `seq30`)**: 30bp 基因组靶标全长序列，严格布局为：4nt 5'侧翼 + 20nt 间隔序列 (Guide) + 3nt PAM (NGG) + 3nt 3'侧翼。
- **引导序列 (`Guide Sequence` / `seq20`)**: 20nt 的特异性识别序列（位于 `seq30` 的第 4–24 索引切片）。
- **种子区 (`Seed Region` / `seed_6nt`)**: 引导序列第 15–20 位（紧邻 PAM 5'端），Cas9 核酸酶结合与解旋的核心敏感区。
- **邻近前间区基序 (`PAM` / `pam_3nt`)**: 第 25–27 位的识别基序（须为 NGG，即第 26–27 位为 GG）。首碱基 N 进行 4 维 One-Hot 编码。
- **序列规格值对象 (`SequenceSpec`)**: 领域实体，负责 30bp 序列的强类型校验、区域解构（Guide、Seed、PAM、Flanks）及生物物理特征（GC 含量、Tm、Poly-T）计算。
- **靶位点区域判定 (`Region Classification`)**: 位点在基因结构中的归属：`exon` / `intron` / `promoter` / `intergenic`；启动子为 TSS 上游链感知窗口（`PROMOTER_UPSTREAM` = 2kb）；无外显子粒度数据源（库内基因表、GFF gene 索引）时基因体内按外显子近似标 `exon`。判定规则单点定义在 gene-structure 模块，GFF 外显子粒度与基因体近似共用同一优先级。

---

## 2. 效率预测与模型层 (Efficiency Prediction & Models)

- **金标准数据集 (`noB879`)**: 879 行 / 16 基因组的纯 A 级实测效率数据集，排除 90 行 B 级候选竞争地雷样本，为现行生产模型的唯一基准。
- **形态二生产模型 (`v2.1 Hierarchical Beta-Binomial GLMM`)**: 融合 DeepSpCas9、CRISPRon 及 8 维生物物理特征，采用分层贝叶斯选择性经验贝叶斯（Selective EB）收缩机制剥离批次随机扰动，推断纯序列生物学活性 $\eta = \beta_0 + Z\beta$。
- **相对排序效率分 (`efficiency_score`)**: 模型输出的相对活性量度（0.0–100.0），用于同一基因内候选 guide 的择优排序推荐（非绝对 indel% 承诺）。
- **CRISPRon 来源标注 (`crispron_source`)**: 该维特征的来源标识：`wsl_real` 为 WSL 原生容器实跑模型；`approximated` 为管线不可用时的物理经验近似式降级值，前端必须如实提示用户。（Docker 容器部署时经镜像内原生管线实跑，同样标 `wsl_real`，语义=真实模型实跑、与训练集同管线。）
- **推理客户端接缝 (`InferenceClient`)**: 跨进程环境适配器，隔离宿主服务环境与 TensorFlow/Genet 环境，负责 Python 解释器自愈探测、Windows DLL 注入、IPC 序列化及降级状态结构化返回。
- **CRISPRon 来源裁决 (`CrispronScorer`)**: `crispron_source` 不变量的唯一执行点——真实模型优先，逐条降级为经验近似式并如实标注 `approximated`，绝不冒充 `wsl_real`；降级决策与标注不再由调用方各自承担。
- **模型分缺失标注 (`未计算`)**: 模型推理不可用或未产出分数时，`efficiency_score` 如实留空并标注「未计算」，绝不以 GC 等启发式公式编造数值（对齐「不硬猜」纪律）；`crispron_source` 仅在有 CRISPRon 分时标注来源，无分不标注。

---

## 3. 多组学图谱与决策引擎 (Multiomics & Decision Engine)

- **跨物种注释映射 (`Crosswalk LSA↔T2T`)**: 莴苣 T2T 染色体组装与 v1.1c (LSA) 转录组表达之间的分级对应关系。demo 面板 49 基因（16 号脚本）与全基因组 45,981 基因（18 号批量定位引擎）共用同一 tier 语义与「不硬猜」纪律。
- **表达证据状态 (`ExpressionStatus`)**:
  - `mapped`: 精确 1:1 映射至唯一 LSA 基因座；
  - `mapped_cluster`: 映射至串联重复基因簇（Tandem Cluster）；
  - `mapped_scaffold`: 映射至未挂载染色体的 scaffold 序列；
  - `unmappable`: 序列缺失或注释缺口，不编造表达值，标记为表达证据缺失。
- **组织优先指数 (`TissuePriorityIndex` / 方案3)**:
  $$\text{PriorityScore}(i, t) = 0.50 \cdot \text{Percentile}(\text{EffScore}_i) - 0.25 \cdot \text{Penalty}(\text{OffTarget}_i) + 0.25 \cdot S(E_t(g))$$
  融合靶向效率、脱靶惩罚与目标组织表达激活的综合推荐排序。
- **功能性脱靶危害 (`FunctionalOfftargetHazard` / 方案5)**:
  评估 gRNA 对面板内关键功能基因座的潜在误伤，以错配权重及非靶标组织表达量进行加权。
- **产胶发育时相窗口 (`DevelopmentalWindow` / 方案6)**:
  橡胶草根部及胶乳组织 S1–S9 发育时相表达动力学，标定天然橡胶生物合成通路（REF/SRPP/CPT）推荐遗传转化窗口（S4）。
- **候选推荐引擎 (`CandidateRankingEngine`)**:
  负责数据装载、多组学属性合并、着丝粒/外显子区域过滤、多目标动态排序调度及展示列头语义转换的核心领域引擎。
- **排序语义单点定义 (`ranking_semantics`)**: 组织优先指数、功能性脱靶危害及其表观折中变体的公式、权重与公式文案的唯一定义处；科研轨、全栈轨与导出方法学共用同一来源，不得各自复述。

---

## 4. 全栈服务与持久化模型 (Full-Stack & Persistence Entities)

- **打分作业 (`ScoringJob`)**: 异步计算任务实体，生命周期包含 `pending` -> `running` -> `completed` / `failed`。负责封装输入序列列表、模型路由配置、进程执行日志及各推理阶段耗时。
- **靶位点候选记录 (`TargetCandidateRecord`)**: 领域持久化实体，记录 gRNA 靶位点基因座、染色体物理坐标、序列规格、预测效率分、脱靶风险等级及多组学组织优先分。
- **实验设计导出批次 (`ExportBatch`)**: 用户经由多条件组合筛选（着丝粒回避、外显子定位、组织特异性加权）后固化并导出的实验设计下单与验证方案清单。
- **批量打分生命周期 (`BatchScoringSession`)**: demo 批量导入流程的属主——上传表 → 校验批次 → 打分 + ATAC 标注结果集；缓存键构成、动态超时与结果拼装策略内聚于此，batch_importer 仅作 IO 适配。
- **候选查询模块 (`CandidateQuery`)**: 全栈候选检索的前端接口——筛选状态进、`CandidatesResponse` 出；请求编码与区域过滤优先级规则（`region_type` 优先于 `exon_only`）在此单点定义，导出前的脱靶预计算编排亦隐藏于此。

