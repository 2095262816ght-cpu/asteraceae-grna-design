# 菊科菊苣族多组学转录表达数据六大应用方案实施计划与流水线全景规范

> **文档性质**：现行技术实施方案与流水线开发最高依据  
> **制定基准日**：2026-09-23  
> **数据基石**：[`data/expression/`](file:///D:/lifesciencechallenge/cs_pipeline/data/expression/)（2026-09-22 接收并规范入库）  
> **关联依据**：
> - [`docs/project_progress_report.md#七、新发多组学转录组表达数据（newdata）全景应用方案与重算路径评估`](file:///D:/lifesciencechallenge/cs_pipeline/docs/project_progress_report.md)
> - [`docs/plans/division_plan_cs.md`](file:///D:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_cs.md)（计算机系实施标准）
> - [`docs/plans/division_plan_master.md`](file:///D:/lifesciencechallenge/cs_pipeline/docs/plans/division_plan_master.md)（接口协议与交付里程碑）

---

## 一、战略定位与设计原则

根据团队最新决策，本项目不再拘泥于“是否需要重新计算”，而是以**“能否带来实质性科学增益、能否在生命科学挑战赛评审中建立绝对压制力”**为唯一导向。新发表达矩阵数据的入库，标志着本项目正式由“单模态序列打分器”向**“序列–表观–转录联合驱动的植物多组学 CRISPR 智能设计平台”**实施质变跃迁。

### 1. 核心指导原则
1. **轻重结合，攻守兼备（双轨制）**：
   - **保底交付轨（主分支 `main`）**：以极小代码改动快速集成前端多组织看板（方案 1）与组织推荐重排（方案 3），确保 100% 具备稳定可交付、可录屏的成果；
   - **冲刺突破轨（分支 `feature/multiomics-pipeline`）**：全面推翻传统纯序列约束，实施多组学特征提取与模型重训（方案 4）、组织功能性脱靶危害度加权（方案 5）及橡胶草产胶时相挖掘（方案 6），全力冲击 LOGO-CV $\rho \ge 0.50$ 达标线。
2. **端到端解耦与模块化**：新增流程以 `scripts/16` ~ `22` 系列独立编号脚本承载，数据流向清晰，每个环节均设置断言守卫（Assertion Guard）与质控日志，确保完全可追溯、可复现。
3. **生物学意义闭环**：所有算法产物必须服务于明确的育种目标——**叶片抗病（莴苣 NLR）**、**茎秆品质（莴笋）**与**胶乳高产（橡胶草 TKS）**。

---

## 二、数据基石与标准化数据流（I/O Contract）

```mermaid
graph TD
    classDef raw fill:#e2e3e5,stroke:#383d41,color:#383d41;
    classDef proc fill:#d1ecf1,stroke:#0c5460,color:#0c5460;
    classDef feat fill:#fff3cd,stroke:#ffc107,color:#856404;
    classDef out fill:#d4edda,stroke:#28a745,color:#155724;

    A1["data/expression/1-3_lettuce_5tissue_expression_matrix.csv<br>(莴苣 40,267 基因 × 5 组织)"]:::raw
    A2["data/expression/lettuce_biorep_expression_matrix.csv<br>(莴苣 16 批次生物学重复)"]:::raw
    A3["data/expression/2-3_TKS_Tiss-Dev-Expression(1).xlsx<br>(橡胶草 36,239 基因 × S1-S9 80 样本)"]:::raw
    R1["data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff"]:::raw
    R2["data/reference_genomes/1-3_Stem_lettuce_ATAC_peaks.xlsx"]:::raw
    R3["data/1_Hi-results-16.1-efficiency-20260921.xlsx<br>(现行交付版 969/879 行)"]:::raw

    B1["预处理与归一化脚本<br>scripts/16_prep_expression_features.py"]:::proc
    A1 --> B1
    A2 --> B1
    A3 --> B1
    R1 --> B1
    R2 --> B1
    R3 --> B1

    F1["橡胶草训练集多组学特征表<br>results/feature_matrix_multiomics_tks.csv"]:::feat
    F2["莴苣全外显子组织表达特征库<br>results/lettuce_gene_expression_features.parquet"]:::feat
    B1 --> F1
    B1 --> F2

    F1 --> P4["方案4: 多组学模型重训<br>(scripts/18, 19, 20)"]:::out
    F1 --> P2["方案2: 特征消融实验<br>(scripts/17)"]:::out
    F2 --> P1["方案1: Demo 组织表达看板<br>(app/app.py)"]:::out
    F2 --> P3["方案3: 组织特异推荐重排<br>(scripts/21)"]:::out
    F2 --> P5["方案5: 组织功能脱靶危害分<br>(scripts/22)"]:::out
    A3 --> P6["方案6: 橡胶草时相编辑窗口<br>(scripts/23)"]:::out
```

### 1. 数据对齐与映射字典规范
- **莴苣体系**：
  - 表达矩阵基因 ID：`LSA1` ~ `LSA40268`（茎用莴苣 v1.1c 标准）；
  - 映射转换：编写 `map_lsa_to_t2t(lsa_id)` 工具函数，通过 BLASTP/Orthofinder 或坐标同源重叠，实现 `LSA` 编号与 T2T 基因组 `LsaT2T...` 编号的双向映射；
  - 组织字段：`Root`（根）, `Stem`（茎）, `Leaf`（叶）, `Flower`（花）, `Seed`（种子）。
- **橡胶草体系**：
  - 表达矩阵基因 ID：`evm.model...`（TKS EVM 注释集）；
  - 与训练集对齐：原 Hi-TOM 11 个核心靶基因（如 `EVM.MODEL.LG05.2725`）不区分大小写，经字符串规范化后直接索引；
  - 组织时期字段（共 80 样本）：
    - 根：`S1-gen` ~ `S9-gen`（各 3 重复）；
    - 叶：`S1-ye` ~ `S9-ye`（各 3 重复）；
    - 胶乳：`S4-jiaoru` ~ `S9-jiaoru`（各 3 重复）；
    - 花与花葶：`S6-hua`、`S6-huating`（各 3 重复）。

### 2. 多组学表达特征指标定义（Mathematical Definition）
在后续特征工程中，针对每个基因 $g$，统一提取以下数值特征：
1. **组织表达基线水平**：$E_{\text{tissue}}(g) = \log_2(\text{TPM}_{\text{tissue}}(g) + 1)$；
2. **全组织最大表达量**：$E_{\max}(g) = \max_{t} E_t(g)$；
3. **全组织平均表达量**：$E_{\text{mean}}(g) = \frac{1}{T} \sum_{t=1}^T E_t(g)$；
4. **组织特异性指数（Tau Index）**：
   $$\tau(g) = \frac{\sum_{t=1}^T \left(1 - \frac{\text{TPM}_t(g)}{\max_t \text{TPM}_t(g)}\right)}{T - 1} \quad \in [0, 1]$$
   （$\tau \to 1$ 表示极度特异，$\tau \to 0$ 表示管家基因泛表达）；
5. **表达变异系数**：$CV(g) = \frac{\sigma(g)}{\mu(g) + \epsilon}$。

---

## 三、六大方案分步实施计划与流水线规范

### 方案 1：【免重算·前端增强】Web Demo 靶基因多组织表达动态看板与表型预警

#### 1. 目标与定位
在不改变现有模型打分与脱靶文件的基础下，升级 Streamlit Demo，用户在查询任意基因时，实时呈现该基因在根、茎、叶、花、果（及橡胶草胶乳）的表达丰度与组织特异性敲除风险。

#### 2. 流水线与代码变更
- **涉及文件**：
  - [NEW] [`app/expression_visualizer.py`](file:///D:/lifesciencechallenge/cs_pipeline/app/expression_visualizer.py)：表达量查询与 Plotly/Altair 渲染引擎模块；
  - [MODIFY] [`app/app.py`](file:///D:/lifesciencechallenge/cs_pipeline/app/app.py)：Tab 1 基因详情侧边栏/主卡片接入看板组件。
- **具体逻辑实现**：
  1. `load_expression_data()`：利用 `@st.cache_data` 预加载 `1-3_lettuce_5tissue_expression_matrix.csv`（1.5MB，内存开销 < 5MB，瞬间加载）；
  2. 根据当前选中的目标基因提取其 5 组织 TPM 值；
  3. 绘制水平条形图（使用绿/蓝冷色系渐变，符合生科 UI 风格）；
  4. **表型安全诊断桩**：
     - 若当前目标组织 $\text{TPM} < 0.5$：输出 warning *“⚠️ 弱表型警示：该基因在所选组织中转录静默（TPM < 0.5），CRISPR 敲除可能无法诱导明显生物学表型”*；
     - 若 $\text{TPM} \ge 10.0$：输出 success *“✅ 适宜靶向：该基因在所选组织中高度转录，染色质处于开放状态，预期编辑响应好”*。
- **工时预估**：0.5 小时。
- **验收命令**：
  ```bash
  conda run -n grna-demo streamlit run app/app.py
  ```

---

### 方案 2：【免重算·科研增量】转录组特征对 Hi-TOM 编辑效率的消融验证（Ablation Study）

#### 1. 目标与定位
利用原 Hi-TOM 实验 11 个橡胶草靶基因 100% 命中新表达矩阵的契机，定量回答审稿人与评委的必问问题：*“在植物 CRISPR 编辑中，靶基因的转录表达水平究竟在多大程度上影响剪切效率？”*。

#### 2. 流水线脚本与工序
- **核心脚本**：[NEW] `scripts/17_ablation_expression_features.py`
- **执行步骤**：
  1. **提取对齐**：读取 `data/1_Hi-results-16.1-efficiency-20260921.xlsx` 中的 `train969` 与 `noB879` 样本，按靶基因 `gene_id` 从 `2-3_TKS_Tiss-Dev-Expression(1).xlsx` 中提取对应的根（gen）、叶（ye）、胶乳（jiaoru）的基线表达量；
  2. **构建特征组对照**：
     - Group A（基线组）：纯序列理化特征 + DeepSpCas9 + CRISPRon 分数；
     - Group B（多组学组）：Group A + $\log_2(\text{TPM}+1)$ + $\tau$ 指数 + 发育均值；
  3. **评估矩阵**：
     - 按现行标准运行 17 折留一基因交叉验证（LOGO-CV）；
     - 采用 Wilcoxon 符号秩检验评估 $\Delta \rho$ 的统计显著性；
     - 输出 SHAP 特征重要性条形图（`results/ablation_expression_shap.png`）。
- **产出成果**：
  - `results/ablation_expression_study_0923.csv`（逐折 Spearman $\rho$ 对比表）；
  - `results/ablation_expression_report_0923.md`（作为申报报告与论文的独立章节）。
- **工时预估**：1.0 小时。

---

### 方案 3：【中度重算·业务重排】构建「组织特异多组学优先指数（Priority Score）」全基因候选重排

#### 1. 目标与定位
彻底解决传统工具“脱靶低、效率高但基因根本不表达”的盲目敲除痛点。在不改变序列本身效率分与脱靶数的前提下，根据目标器官需求重新排序，为用户推荐既切得准、又在目标组织切实起效的最佳 gRNA。

#### 2. 流水线脚本与数学模型
- **核心脚本**：[NEW] `scripts/21_build_tissue_priority_recommendations.py`
- **算法设计（Multi-objective Pareto Rank）**：
  针对候选 gRNA $i$，在其所属基因 $g$ 与指定目标组织 $t$ 下，定义综合推荐指数：
  $$\text{PriorityScore}(i, t) = 0.50 \cdot \text{Percentile}(\text{EffScore}_i) - 0.25 \cdot \text{Penalty}(\text{OffTarget}_i) + 0.25 \cdot \mathcal{S}(E_t(g))$$
  其中：
  $$\mathcal{S}(E) = \frac{1}{1 + e^{-(E - 2.0)}} \quad (\text{表达量 Sigmoid 激活打分，饱和值 } 1.0)$$
  $$\text{Penalty}(\text{Off}) = \min\left(1.0, \, \frac{\text{mis0}\times 1.0 + \text{mis1}\times 0.5 + \text{mis2}\times 0.2 + \text{mis3}\times 0.05}{10.0}\right)$$
- **执行流程**：
  1. 读取 `demo/app_data.csv` 中的全部 demo 候选 gRNA；
  2. 关联 `1-3_lettuce_5tissue_expression_matrix.csv` 对应组织表达量；
  3. 针对 Root / Stem / Leaf / Flower / Seed 5 种模式分别生成排序列：`priority_rank_leaf`, `priority_rank_stem` 等；
  4. 落盘为 `demo/app_data_tissue_priority.csv` 并联动至前端。
- **工时预估**：2.0 小时。

---

### 方案 4：【重度重算·核心冲刺】打造国际首个菊科多组学（序列 + 转录 + 表观）CRISPR 效率预测模型

#### 1. 目标与定位
**接受推翻重训的顶级攻坚路线**。打破纯序列瓶颈，将基因转录活性（RNA-seq）、染色质松散度（ATAC-seq）及 RNA Pol II 链转录冲突效应融为一体，构建全新的端到端预测模型，全力冲刺 LOGO-CV $\rho \ge 0.50$。

#### 2. 多组学特征集体系设计（4 大维度 32 个特征）

```mermaid
graph TD
    classDef seq fill:#cce5ff,stroke:#004085,color:#004085;
    classDef pre fill:#e2e3e5,stroke:#383d41,color:#383d41;
    classDef epi fill:#fff3cd,stroke:#856404,color:#856404;
    classDef rna fill:#d4edda,stroke:#155724,color:#155724;

    subgraph 维度1: 纯序列与热力学理化特征 (16维)
        S1["单核苷酸/双核苷酸位置编码 (Pos 1-20)"]:::seq
        S2["GC 含量, Tm 溶解温度, 自由能 ΔG"]:::seq
        S3["连续 Poly-T 长度, PAM 前后碱基偏好"]:::seq
    end

    subgraph 维度2: 预训练模型迁移基线 (2维)
        P1["DeepSpCas9 on-target 分数"]:::pre
        P2["CRISPRon 综合分数 (WSL 真实调用)"]:::pre
    end

    subgraph 维度3: 染色质表观可及性 (6维)
        E1["是否落入 ATAC-seq Peak (0/1)"]:::epi
        E2["距最近 ATAC 开放峰中心绝对距离 (bp)"]:::epi
        E3["ATAC 峰信号富集强度 (Fold Enrichment)"]:::epi
    end

    subgraph 维度4: 转录组与聚合酶碰撞动力学 (8维)
        R1["靶基因稳态表达量 log2(TPM+1)"]:::rna
        R2["组织特异性指数 τ 与跨样本变异系数 CV"]:::rna
        R3["转录链冲突标志位 (NTS 靶向非模板链 vs TS 模板链)"]:::rna
        R4["外显子转录本丰度加权活性"]:::rna
    end
```

#### 3. 流水线脚本与工序分解
- **脚本 1：多组学特征工程提取器**
  - [NEW] `scripts/18_build_multiomics_features.py`
  - 整合 `1-1_Stem_lettuce_v1.1c.gff`（提取链向与转录起始点 TSS）、`1-3_Stem_lettuce_ATAC_peaks.xlsx`（染色质区间覆盖）及 `data/expression/`（表达量）；
  - 产出高维特征矩阵：`results/feature_matrix_multiomics_full_0923.csv`。
- **脚本 2：多组学分层模型重训**
  - [NEW] `scripts/19_train_multiomics_glmm.py`
  - 架构选择：基于**形态二（分层选择性 Beta-Binomial GLMM）**扩展多组学协变量；
  - 似然层直接拟合测序深度与 indel 分子，固定效应同时吸收序列特征与多组学特征向量：
    $$\eta_i = \beta_0 + \mathbf{x}_{\text{seq}}^\top \boldsymbol{\beta}_{\text{seq}} + \mathbf{x}_{\text{atac}}^\top \boldsymbol{\beta}_{\text{atac}} + \mathbf{x}_{\text{rna}}^\top \boldsymbol{\beta}_{\text{rna}} + u_{\text{batch}(i)}$$
- **脚本 3：全流程 LOGO-CV 验证与模型冻结**
  - [NEW] `scripts/20_eval_multiomics_logo.py`
  - 严格执行 17 折留一基因交叉验证，防泄漏评估；
  - **决策守卫**：
    - 若 LOGO 中位数 $\rho \ge 0.50$：落盘为 `results/meta_model_multiomics_best_0923.joblib`，替换 `scripts/predict.py` 默认模型，全量重跑 19,839 条候选打分并重构 Model Card；
    - 若未达 0.50：完整归档折级明细，作为负结果对照写入论文。
- **工时预估**：1.5 ~ 2 天。

---

### 方案 5：【重度重算·脱靶革新】组织功能性脱靶危害评估（Tissue-specific Functional Off-target Hazard）

#### 1. 目标与定位
颠覆当前 Cas-OFFinder 仅按序列错配几何计数的低阶模式，提出**“组织功能性脱靶危害指数（Hazard Score）”**。若脱靶点落在目标组织中转录静默的异染色质死区，其剪切毒性极小；若落在高表达管家/光合基因，则给予极大惩罚。

#### 2. 流水线脚本与数学算法
- **核心脚本**：[NEW] `scripts/22_calc_tissue_offtarget_hazard.py`
- **数学模型**：
  对任意 gRNA 候选 $g$，其在特定组织 $t$（如叶片）中的功能脱靶危害分为：
  $$\text{Hazard}_t(g) = \sum_{k \in \text{OffTargetHits}(g)} \omega(\text{mismatch}_k) \cdot \left[ 1.0 + \lambda \cdot \log_2(\text{TPM}_t(\text{gene}(k)) + 1) \right]$$
  其中：
  - $\omega(0)=10.0, \, \omega(1)=3.0, \, \omega(2)=1.0, \, \omega(3)=0.2$ 为不同错配阶数的物理接触衰减权重；
  - $\text{gene}(k)$ 为脱靶位点命中的宿主基因（若落在基因间区 Intergenic 则取背景基线值 0.1）；
  - $\lambda=0.5$ 为表达活跃度惩罚敏感因子。
- **工程实现与大规模区间查询**：
  - 针对 6,088,827 个脱靶位点（`results/offtarget_counts_0924.csv` 对应底层大表），利用 Python `polars` / `duckdb` 引擎将脱靶坐标与 GFF3 外显子坐标区间快速关联（`Interval-Join`）；
  - 批量灌入 40,267 基因的组织表达量，并行聚合计算出每条 candidate gRNA 的组织脱靶危害分；
  - 产出：`results/offtarget_functional_hazard_0923.csv`。
- **工时预估**：4.0 ~ 6.0 小时。

---

### 方案 6：【时相挖掘·特色创新】橡胶草产胶发育时相最佳编辑转化窗口预测

#### 1. 目标与定位
聚焦橡胶草（TKS）国家战略经济性状（天然橡胶替代来源），深挖 S1–S9 共 9 个发育时期的 80 样本高分辨率表达谱，为产胶关键基因提供**最佳转基因/诱导敲除的时序窗口建议**。

#### 2. 流水线脚本与实施步骤
- **核心脚本**：[NEW] `scripts/23_tks_developmental_window.py`
- **处理步骤**：
  1. **靶向通路基因锁定**：梳理橡胶生物合成（Natural Rubber Biosynthesis）核心基因家族：
     - *SRPP*（小橡胶粒子蛋白，Small Rubber Particle Protein）
     - *REF*（橡胶延伸因子，Rubber Elongation Factor）
     - *CPT* / *HRT*（顺式聚异戊二烯转移酶，cis-Prenyltransferase）
  2. **时序表达动力学曲线拟合**：
     - 提取这批基因在 S1~S9 根（根部为产胶主器官）与 S4~S9 胶乳中的 TPM 动力学；
     - 采用三次样条（Cubic Spline）平滑拟合，计算一阶导数 $\frac{d(\text{TPM})}{dt}$（转录爆发增长率）；
  3. **算法输出转化窗口卡片**：
     - 输出量化建议：*“推荐在 S4 幼苗期（胶乳初生期）启动 Cas9 诱导表达，此时靶基因表达活跃度上升 3.8 倍、染色质充分松散，同时幼苗分生组织具备极高再生分化能力”*。
- **产出成果**：
  - `results/tks_rubber_pathway_dynamics.png`（9 阶段动态折线图）；
  - Demo Tab 1 中集成“橡胶草产胶时相决策组件”。
- **工时预估**：3.0 小时。

---

## 四、甘特排期与执行调度表（End-to-End Orchestration）

为了在保证绝对安全交付的同时全力冲刺高分，流水线划分为 **4 个冲刺冲程（Sprints）**：

| 阶段 / 冲程 | 重点任务与交付脚本 | 耗时预估 | 负责角色 | 交付产物与验证节点 |
|---|---|:---:|:---:|---|
| **第一冲程：基础库搭建与保底集成（P0）** | ① 建立 `scripts/16_prep_expression_features.py`<br>② 完成**方案 1**（Demo 前端表达量看板）<br>③ 完成**方案 3**（组织优先指数重排） | 0.5 天 | 计B / 计A | • Demo 具备根/茎/叶/花/果看板与表型警告<br>• 生成 `app_data_tissue_priority.csv`<br>• **确保随时可录屏、可交付保底成果** |
| **第二冲程：科研消融与时相挖掘（P1）** | ① 执行**方案 2**（Hi-TOM 表达量消融脚本 `scripts/17`）<br>② 执行**方案 6**（橡胶草 S1-S9 时序挖掘 `scripts/23`） | 0.5 天 | 计A / 生C | • 产出 `ablation_expression_study_0923.csv`<br>• 产出橡胶草产胶发育窗口动态图<br>• 形成学术报告第 7 节支撑材料 |
| **第三冲程：模型重训顶级攻坚（P1·重来）** | ① 执行**方案 4**（构建序列+ATAC+RNA多组学特征大表 `scripts/18`）<br>② 重训多组学分层 GLMM 模型（`scripts/19`）<br>③ 执行 LOGO-CV 全量检验（`scripts/20`） | 1.5 天 | 计A | • 检验 $\rho \ge 0.50$ 达标线<br>• 若达标：全量替换生产模型权重与 Model Card<br>• 若未达标：归档为科学消融附录 |
| **第四冲程：脱靶革新与综合验收（P2）** | ① 执行**方案 5**（608 万脱靶位点组织危害度加权 `scripts/22`）<br>② 全流水线断言校验与最终冻结会签 | 0.5 天 | 计B / 全员 | • `offtarget_functional_hazard_0923.csv`<br>• 全流程文档汇总与视频录制脚本就绪 |

---

## 五、质量保证与风险熔断机制（Fall-back Protocol）

1. **版本与分支隔离铁律**：
   - 现行交付基准 `v2.0-freeze`（包含已通过两轮审计的 16.1 效率分与 Demo）在 `main` 分支保持不动；
   - 方案 4（多组学模型重训）必须在独立分支 `feature/multiomics-pipeline` 运行，严禁在验证通过前覆写 `meta_model_hier_bb_nob879_0921.joblib`；
2. **多组学指标验收熔断条件**：
   - **通过标准**：多组学模型的 17 折 LOGO-CV 中位数 $\rho_{\text{multiomics}} \ge 0.50$，且在无 B 级脏数据测试集上保持正相关（$\rho_{\text{test}} > 0.35$）；
   - **熔断回退**：若多组学引入后发生过拟合（$\rho$ 不升反降），立即启动熔断机制：生产环境维持纯序列形态二 GLMM 权重，将多组学特征作为“方案 2 消融研究成果”写入报告，确保比赛交付万无一失！
