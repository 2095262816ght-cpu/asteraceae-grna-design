# 答辩学习 05：软件系统与工程实现

> **用途**：应对"工具怎么用？架构怎么设计的？降级怎么处理？可部署吗？"一类追问。
> **深挖入口**：`docs/adr/`（4 份架构决策记录）、`docs/reports/FULLSTACK_DELIVERY_ACCEPTANCE.md`（验收）、`docs/USER_MANUAL.md`（用户手册）、`core/` 与 `app/` 源码。

---

## 1. 全栈架构（PostgreSQL + FastAPI + React）

### 1.1 为什么重构全栈（ADR 0004 四痛点）

① Streamlit 无持久化，刷新即丢打分/筛选/导出记录；② 双模型推理耗时长，单线程阻塞冻结 UI；③ 19,839 条候选与多组学特征常驻内存 DataFrame，无法高并发 SQL 过滤/分页；④ 难做基因组图谱高密度渲染与复杂表单。

### 1.2 架构决议（洋葱三层）

```
cs_pipeline/   纯领域算法层（禁引 FastAPI/SQLAlchemy/前端依赖）
   ├── core/    SequenceSpec · ranking_semantics · atac_annotator（值对象与公式单点）
   └── app/     InferenceClient · CandidateRankingEngine · BatchScoringSession · batch_importer
backend/       REST + PostgreSQL + Alembic + TaskRunner（Repository/Adapter 无侵入封装领域层）
frontend/      Vite + React 19 + TypeScript + Tailwind + shadcn/ui + TanStack Query + ECharts
```

- **PostgreSQL 16 分层存储**：核心表（`target_candidates` 19,839 条、`scoring_jobs`、`export_batches`）结构化入库 + B-Tree 索引（`(gene_id, efficiency_score)` 复合索引）；超大只读矩阵保持 Parquet/文件。
- **任务状态机**：`ScoringJob`：`pending → running → completed / failed`（UUID 主键、total/processed 进度、`crispron_source`、warning/error_message、duration）；前端 TanStack Query 在 running 时每 **1.5s** 轮询。
- **库规模**：46,030 基因（45,981 全基因组 + 49 NLR）/ 4,549,329 候选；按基因查询 count≈1ms、top50≈5ms。

### 1.3 双轨一致性验收（可引用数字）

| 项 | 数字 |
|---|---|
| 垂直切片 | Ticket 01–07 全部完成（含 commit 号） |
| 双轨数值比对 | 49 基因元数据 100% 吻合；抽样基因排序前 10 位点 ID/链/PAM/30bp 完全一致，GC 误差 <0.01%、Tm 误差 <0.01°C、效率分误差 <0.001 |
| 序列解构一致性 | 100%（示例 30bp → 侧翼/Guide/PAM 解构与黄金基准逐字段一致） |
| 自动化测试 | 0926 验收：后端 17 / 前端 13；0929 教师反馈后：后端 **65/65**、前端 **25/25**（引用时注明时点） |
| 部署 | `docker compose up --build -d`（前端 :80/:3000、Swagger :8000/docs、PG 5432）；或 `一键启动全栈系统.bat` |

---

## 2. 深度模块设计（ADR 0001–0003，工程能力的核心证据）

设计原则：**Deep Module**——接口简单、实现深藏；改动一处、生效全局；可脱离 UI 纯 Python 单测。

### 2.1 SequenceSpec（ADR 0003）——30bp 值对象单一事实来源

- 切片常量单点：`FLANK_5P[0:4] / GUIDE[4:24] / SEED[18:24] / PAM[24:27] / PAM_N[24:25] / FLANK_3P[27:30]`；
- 校验规则：必须字符串 → 长度 30 → `^[ACGT]{30}$` → 第 25–27 位须 NGG（即 26、27 位为 GG）；
- 物理特征：GC、Tm（Biopython Tm_NN 优先，缺 Bio 时降级纯 Python SantaLucia 1998 近邻参数模型，精度对齐）；
- 输出 9 个派生特征列（`SEQ_FEATURE_COLS`），**训练与推理同源**（`features_common.seq_features` 向量化适配器）；
- 背景：此前 30bp 定义分散漂移（app 正则 / predict assert / Wallace 与 Tm_NN 两种 Tm 口径），统一后杜绝 off-by-one 与口径不一致。

### 2.2 InferenceClient（ADR 0001）——跨环境推理接缝

- **接口**：`score_sequences(list[str], timeout_s) -> BatchInferenceResult`（frozen dataclass：raw_df、display_df、latency、n_approximated、warning_message）。
- **为什么需要**：genet 锁 TF<2.10 与宿主环境冲突 → 推理必须跑独立 conda 环境子进程；若把"探测解释器、注入 Windows DLL 路径、subprocess stdin/stdout CSV 协议、异常转换"写进 UI，代码无法测试。
- **自愈探测顺序**：`CRISPR_PYTHON` 环境变量 → 环境相对路径 → CONDA_* 推导 + 多盘符 Miniconda/anaconda 扫描 → 兜底 `"python"`（不写死绝对路径，符合《附件5》）。
- **异常层级**：`InferenceError → InferenceTimeoutError / InferenceEnvironmentError / InferenceExecutionError`（分别给出可操作提示）。
- 收益（ADR 记载）：UI 减约 50 行样板、一处修改到处生效、可快速单测。

### 2.3 CandidateRankingEngine（ADR 0002）——多组学重排引擎

- `load_from_directory()` + `rank(gene_id, target_tissue, sort_intent, region_types, hide_centromere) -> RankingResult`；
- 职责：多表左连接（组织优先表 + 危害表 + ATAC）、着丝粒/区域过滤、**效率列 4 级版本自适应回退**（v21 → full_0916 → efficiency_score → 占位分，每级配模型定位声明文案）、`expression_status` 四态中文化、列头语义转换（`n_intra_panel_sites→面板内位点数` 等）；
- 排序意图常量：`SORT_PRIORITY / SORT_PRIORITY_ATAC / SORT_EFFICIENCY / SORT_OFFTARGET_MIS3 / SORT_GC_MID`（GC 距 50% 绝对值升序）。

### 2.4 ranking_semantics（补充单点）——公式与文案唯一定义处

科研轨、推荐引擎、后端、导出方法学共用同一公式/权重/文案函数——**数字不得漂移**（见 defense_04 §4）。

---

## 3. 诚实标注与降级机制（本项目工程伦理卖点）

### 3.1 CRISPRon 来源裁决（`crispron_scorer.py` 单点不变量）

- 真实模型（WSL/容器原生）优先 → 逐条降级为经验近似式 **`approx = deepspcas9×0.95 + (Tm−50)×0.25`** 并标注 `approximated`，**绝不冒充 `wsl_real`**；
- 历史教训（写在注释里）：曾有 predict.py 与 scripts 各持副本、漏标即"推理期特征伪造"（P0 事故，已收口为单点裁决）；
- 前端如实提示：`wsl_real` 绿徽标"真实模型实跑"；`approximated` 琥珀徽标"经验近似式降级值，实测可偏约 15%"；未产出显示"未计算"。

### 3.2 全系统"缺啥写啥"纪律（USER_MANUAL §6）

| 场景 | 行为 |
|---|---|
| 脱靶未扫描 | 显示"未计算"，**不写 0** |
| 表达不可映射 | "表达证据缺失"，不编造 TPM |
| 效率分不可用 | 留空 + 警告，不用 GC 启发式编造（占位分必须显著标注"非模型预测"） |
| 未锚定序列 | 多组学"无法计算"，不硬算 |
| 导出 | 逐行携带"缺失原因 / 所需数据 / 所用参考包"三列 + 《指标方法说明》sheet |

### 3.3 批量打分生命周期（`BatchScoringSession` / `batch_session.py`）

上传表 → 校验批次（序列列/ID 列智能探测：关键词权重 + 内容采样）→ 打分（缓存键 = 文件 MD5 + 工作表 + 列名防脏读；动态超时 `max(180, n×5+60)`）→ ATAC 标注 → 拼装导出。全栈侧分块推理（约 8 个进度台阶、单块超时 180s），异常块写 warning"该块模型分未计算"，**未产出分如实留空**。

---

## 4. 用户双轨与使用流程（演示用）

- **双轨**：全栈版（React + FastAPI）+ Streamlit 版（黄金基准，端口 8501）——双轨数值比对 100% 吻合是验收依据。
- **两种核心用法**：
  1. **按基因检索**：选基因（支持全基因组 45,981 个 `LsT2T*` 与 49 个 NLR `LsaT2T*` 双命名空间，前缀标注注释来源）→ 多条件筛选（着丝粒回避、外显子定位、组织加权）→ 排序推荐表（融合效率分、组织优先指数、功能性脱靶危害）→ 取 top 3–5 送实验终筛；
  2. **按序列打分**：贴入 30bp → 四段即时校验（长度→字符→PAM→绿字合规）→ 分子解构 + 10 维特征 + 双模型分 + 表达适配度三卡（Poly-T 硬过滤提示 / 5'G 标记 / MFE<−5 kcal/mol 警示）→ 三态注释（命中预计算候选/基因组回贴命中/自定义未锚定）。
- **效率百分位三档口径**（9.29 D3）：库内该基因预计算分布 → 现场枚举同基因候选+批量打分 → 贴入集合百分位（批内排名口径，显著标注）；单条无集合不排名。

---

## 5. 部署与离线交付

- **三层 requirements**：`requirements.txt`（评委一键装齐，内含 `-r requirements-score.txt`）；`requirements-score.txt`（打分子进程环境：torch cpu / TF2.9.3 / genet 0.17.2）；`requirements-crispron.txt`（WSL 独立环境 TF2.14 + ViennaRNA 2.6.4）。未装 CRISPRon 环境时其余功能全部不受影响。
- **docker-compose 三服务**：postgres:16-alpine + backend + frontend(nginx)；5 个大数据文件外挂只读挂载（不进镜像），**缺任一文件对应功能优雅降级**。
- **离线交付包** `deploy_offline/`：镜像 tar + sha256 manifest + 导入/停止脚本（校验 Docker Engine、逐项告知缺失数据的降级功能、警告可移动盘/exFAT 挂载不可靠）。
- **外部工具**：Cas-OFFinder v2.4.1（MIT，win64 二进制不随包）；CRISPRon（GPL/AGPL，WSL 脚本重建）；genet 首次 predict 自动下载 checkpoint（约 700KB）。

---

## 6. 工程事故与教训（问"遇到什么困难"时的好素材）

| 事故 | 教训与修复 |
|---|---|
| 测试套件误清真实数据库 | 新规：backend 测试一律 `DATABASE_URL=sqlite+aiosqlite:///./lifescience_test.db` 隔离，严禁对真实库跑测试 |
| crosswalk 命中爆炸 660M 行 OOM | code 级限流 20 条命中 + 最优命中一次选择传播，杜绝命中×guide 双重扇出 |
| 着丝粒 Chr1 vs Chr01 字符串匹配恒 False | 染色体名规范化统一后区间重叠判定 |
| 效率综合分被人为 tie-break 抖动摊开 | 独立审计发现 → 去抖动、并列同值 + competition ranking |
| scipy cholesky 路径硬崩（exit 127） | 显式 `solver="svd"` + scipy 降级 1.14.1 |
| guide-id 跨文件编号错配 | `_DEPRECATED` 改名 + 禁止按 ID join |

---

## 7. 防雷与口径提醒（本板块）

1. 测试数量三时点并存（17/13 = 0926 验收；18 文件/52 项 = 手册 7.3；65/65+25/25 = 0929 教师反馈后）——引用注明时点。
2. SPEC-0001 写 `POST /scoring/jobs`，实际为 `POST /scoring/single`（批量 `/scoring/upload`）；ADR 0002 接口名 `rank_candidates` 实际 `rank()`——引用接口以实际后端为准（完整清单见 `backend/app/api/v1/endpoints/`）。
3. 效率分免责声明必说：**同一基因内相对排序参考，非绝对 indel% 承诺**；v2.1 上限参考 Class A ρ=0.464。
4. 任意物种 30bp 均可打分（纯序列驱动），但 v2.1 模型训练于橡胶草 Hi-TOM——跨物种使用须声明局限。
