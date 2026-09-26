# 全栈架构升级规格说明书：PostgreSQL + FastAPI 异步任务 + React 现代前端

- **状态**: ready-for-agent
- **文档编号**: SPEC-0001
- **参考 ADR**: [ADR 0004](../adr/0004-fullstack-postgres-fastapi-react.md)
- **本地工单路径**: `.scratch/fullstack-postgres-react/issues/`

---

## Problem Statement

当前菊科 CRISPR/Cas9 基因编辑设计工具基于 Streamlit 单体架构开发。科研人员在进行高通量编辑靶点设计与模型评估时面临以下核心痛点：
1. **状态易失且无法追踪**：Streamlit 页面一旦刷新，所有单序列打分历史、批量导入预测结果以及根据组织特异性精心筛选出的 gRNA 清单全部丢失，无法对历史计算进行持久化与复现。
2. **长耗时计算阻塞交互**：底层深度学习打分模型（DeepSpCas9、CRISPRon）需要调用子进程及跨平台环境，计算耗时从数秒至数分钟不等。在单线程 Web 模式下，页面直接冻结，缺乏异步排队机制、进度通知与任务恢复能力。
3. **数据检索与多维分析受限**：预计算的数十个 NLR 基因候选靶点数据与多组学特征常驻于 Python 内存 DataFrame 中，随着基因库与候选靶点数量增加，无法进行高并发的 SQL 复杂范围过滤（如同时按效率分、外显子区域、着丝粒距离、组织特异性综合筛选）与分页检索。
4. **前端交互与可视化体验受限**：Streamlit 组件无法提供现代生信工作台所需的基因组物理图谱交互缩放（DataZoom）、高密度候选位点对比面板以及平滑的表格多选导出体验。

---

## Solution

通过解耦前后端并引入关系型与异步计算流水线，将现有生信工具升级为开箱即用的现代化全栈科研平台：
1. **数据库层**：引入 PostgreSQL 16，采用分层持久化模型。核心候选靶点、异步打分作业以及用户导出的实验设计批次全部结构化入库，并建立复合 B-Tree 索引；原始超大时相与未加工组学矩阵保持外部只读文件加载。
2. **后端服务层**：构建 FastAPI 异步后端，采用 Repository/Adapter 模式无侵入连接现有生信算法核心。提供标准的 RESTful 接口与基于 PostgreSQL 状态机的异步任务调度器（Task Runner Seam），支持任务提交、进度轮询与状态回调。
3. **前端交互层**：构建现代化 React 19 单页应用，结合 Tailwind CSS 与 shadcn/ui 组件库，利用 TanStack Query 进行服务端状态管理与异步轮询，利用 Apache ECharts 实现高流畅度基因组位点分布可视化与多组学动力学渲染。
4. **工程交付保障**：保留现有 Streamlit 界面作为算法侧比对的黄金参照（Ground Truth）；通过 Docker Compose 与 Alembic 数据库版本迁移工具实现全栈服务一键启动与初始化候选数据自动灌库。

---

## User Stories

1. As a 生信科研人员, I want to 在浏览器中输入或按下拉菜单快速选择目标基因（如 49 个代表性 NLR 基因）, so that 我能快速查看该基因的所有预计算候选 gRNA 靶位点。
2. As a 生信科研人员, I want to 能够按外显子区域、着丝粒回避和最小预测效率分对候选靶点进行复合过滤, so that 我能排除位于着丝粒不稳定区或编辑效率低下的劣质 gRNA。
3. As a 生信科研人员, I want to 能够根据目标组织（如橡胶草根部胶乳、莴苣叶片）动态调整推荐排序权重, so that 系统能够结合转录组表达活跃度优先推荐高表达区域的位点。
4. As a 生信科研人员, I want to 在基因组物理图谱上直观查看各个 gRNA 靶位点的相对位置、正反链分布及效率分热力色阶, so that 我能全景评估靶点在基因外显子结构上的空间布局。
5. As a 生信科研人员, I want to 在表格中快速查看每个候选 gRNA 的 30nt 全长序列、Guide 序列、PAM、脱靶位点数及模型来源标注, so that 我能掌握靶点的分子特征。
6. As a 生信科研人员, I want to 能够多选符合实验要求的候选 gRNA 并一键创建为「导出批次」, so that 我能保存当次筛选结果并下载为符合实验室下单规范的 CSV/Excel 表格。
7. As a 生信科研人员, I want to 输入一段自定义的 30nt 靶位点序列并提交实时打分, so that 系统能够调用深度学习模型（DeepSpCas9 与 CRISPRon）并输出标准化的相对排序效率分。
8. As a 生信科研人员, I want to 上传包含数百条未知序列的 CSV/Excel 批量文件并发起打分作业, so that 后端能够接收并在后台异步执行计算，而不是锁死前端界面。
9. As a 生信科研人员, I want to 在提交批量打分作业后立刻获得任务卡片并看到实时计算进度条, so that 我能明确了解任务执行到哪个阶段（特征提取、模型推理、结果整合）。
10. As a 生信科研人员, I want to 在关闭页面或刷新浏览器后重新打开时依然能查看到历史打分作业列表及计算结果, so that 我不需要重复执行耗时的深度学习推理。
11. As a 生信科研人员, I want to 能够查看打分作业的详细错误日志或优雅降级标识（例如模型以物理经验公式降级运行）, so that 我能明确获知结果的可靠性依据。
12. As a 系统管理员/科研人员, I want to 通过一条简单的命令（如 `docker-compose up`）一次性拉起数据库、后端 API 与前端静态服务, so that 我无需在本地复杂的环境中手动逐一配置 Python、Node.js 与 PostgreSQL。
13. As a 系统管理员, I want to 系统在首次启动时能够自动执行数据库迁移并自动将预置的 49 个 NLR 基因候选数据批量导入数据库, so that 系统部署完成瞬间即可具备完整数据检索功能。
14. As a 算法开发者, I want to 在开发新功能时保留现有 Streamlit 原型运行能力, so that 我能随时对照 React 前端与 Streamlit 基准的计算输出是否严格一致。

---

## Implementation Decisions

### 1. 模块组织与目录划分
- 遵循洋葱架构三段式设计：
  - `cs_pipeline/` 保持干净的领域模型与算法推理，不引入 FastAPI、SQLAlchemy 或前端依赖。
  - `backend/` 负责对外暴露 RESTful API、维护数据库实体、执行 Alembic 迁移以及管理异步 TaskRunner。
  - `frontend/` 负责所有用户界面、状态管理、图表渲染与 API 客户端调用。
- 根目录提供全局编排文件（`docker-compose.yml`）与用于本地热开发的执行脚本。

### 2. 数据库分层持久化与 Schema 契约
- **`target_candidates` (候选靶位点表)**：
  - 核心字段：`id`, `gene_id`, `gene_name`, `chromosome`, `start_pos`, `end_pos`, `strand`, `seq30`, `seq20`, `pam`, `seed_6nt`, `gc_content`, `efficiency_score`, `offtarget_count`, `is_centromere`, `is_exon`, `expression_status`, `lsa_fpkm`, `created_at`。
  - 索引策略：对 `(gene_id, efficiency_score)` 建立复合 B-Tree 索引，对 `chromosome` 建立单列索引。
- **`scoring_jobs` (打分作业表)**：
  - 核心字段：`id` (UUID), `title`, `status` (`pending`, `running`, `completed`, `failed`), `total_sequences`, `processed_sequences`, `config_json`, `error_message`, `crispron_source`, `duration_seconds`, `created_at`, `completed_at`。
  - 关联从表 `scoring_job_items` 存储具体的输入序列、拆解后的 `SequenceSpec` 以及各个模型的输出分数与降级标注。
- **`export_batches` (实验导出批次表)**：
  - 核心字段：`id` (UUID), `batch_name`, `target_gene`, `selected_count`, `export_format` (`csv`/`excel`), `candidates_json`, `created_at`。

### 3. 后端 API 接口契约 (RESTful)
- 候选检索端点：
  - `GET /api/v1/genes`: 获取所有支持的基因元数据列表（含基因名称、候选数、染色体信息）。
  - `GET /api/v1/candidates`: 分页多条件检索接口，支持过滤参数（`gene_id`, `min_score`, `exclude_centromere`, `exon_only`, `tissue_weight`）及动态字段排序。
- 异步打分端点：
  - `POST /api/v1/scoring/jobs`: 提交单序列或批量序列打分任务，立即返回 `job_id` 与初始状态 `pending`。
  - `POST /api/v1/scoring/upload`: 上传 CSV/Excel 批量打分文件并自动解析创建作业。
  - `GET /api/v1/scoring/jobs`: 获取历史打分作业列表（按时间倒序）。
  - `GET /api/v1/scoring/jobs/{id}`: 获取指定作业的实时状态、进度百分比、日志及完成后的打分结果。
- 导出批次端点：
  - `POST /api/v1/exports`: 保存用户勾选的候选靶点清单为导出批次。
  - `GET /api/v1/exports/{id}/download`: 下载该批次的格式化 CSV 或 Excel 文件。

### 4. 异步 TaskRunner 接缝 (Task Runner Seam)
- 后端定义抽象的 `TaskRunner` 接口：
  - `dispatch_scoring_job(job_id: UUID) -> None`
- 首期实现为基于 FastAPI 后台线程池与 Python `ProcessPoolExecutor` 的本地任务执行器，内部通过独立 Session 更新数据库状态机；外部预留接入 Celery / Redis 的同构签名。
- 任务执行器调用现有的 `cs_pipeline.app.inference_client.InferenceClient` 深度模块进行跨进程/WSL 模型推理，完全复用其自愈探测与降级状态解析逻辑。

### 5. 前端交互与状态流转
- 前端核心视图划分：
  - **基因候选检索面板**：基因选择卡片、多组学过滤控制台、ECharts 靶点坐标轴热力图、可虚拟滚动的候选大表及多选导出工具栏。
  - **批量与实时打分工作台**：单序列即时测算卡、表格拖拽上传区、活跃任务轮询卡片（带平滑进度条）及历史任务复查抽屉。
- 状态轮询：使用 TanStack Query 的 `refetchInterval`，当检测到 `job.status` 为 `running` 时每隔 1500ms 自动轮询，并在转为 `completed` 或 `failed` 时停止轮询并弹出反馈通知。

---

## Testing Decisions

### 1. 优秀测试准则
- **只测试外部可见行为，绝不测试内部实现细节**。不测试内部私有变量或 SQL 生成过程，统一以输入请求 $\rightarrow$ 输出响应/数据库状态为验证基准。
- 测试必须具备确定性（Deterministic），在无 WSL 或无真实 GPU 环境下，通过环境模拟与桩数据保证 CI/CD 快速变绿。

### 2. 测试接缝设计 (Seams)
- **后端最高测试接缝**：`TestClient(app)`（基于 FastAPI / HTTP 端点层）。
  - 测试通过发送真实 HTTP 请求，驱动依赖注入、请求校验、数据库持久化及响应序列化全链路。
  - 仅在涉及耗时数十秒的真实深度学习模型调用时，在 `InferenceClient` 接缝处注入假数据（Fake / Stub），验证任务状态机由 `pending` 变为 `completed` 的端到端流转。
- **前端测试接缝**：组件视图渲染测试（基于 Vitest + React Testing Library）。
  - 模拟后端 HTTP 响应，测试用户在界面上的点击、筛选操作以及进度条在接收到轮询状态更新时的 DOM 变化。
- **数据库迁移测试**：针对 Alembic 迁移脚本执行 `upgrade head` 与 `downgrade -1`，确保 Schema 升级与回滚可逆。

### 3. 现有先例与代码参照
- `cs_pipeline/tests/test_inference_client.py`: 提供了对子进程调用、超时处理与异常降级的严密测试范式。
- `cs_pipeline/tests/test_sequence_spec.py`: 提供了针对 30bp 边界条件的值对象测试先例。

---

## Out of Scope

1. **复杂用户权限与租户隔离**：当前系统定位为共享科研工作台模式，不构建用户注册、密码加密找回、团队多租户以及基于角色的访问控制（RBAC）。
2. **全基因组级别的实时在线扫描**：现有管线聚焦于 49 个 NLR 代表基因候选检索与单序列/批量打分，全基因组数十万位点的离线计算与实时扫描算法不在本次全栈改造范围内。
3. **分布式多机调度集群**：首期采用单机容器化架构与轻量异步状态机，跨多节点的分布式 Celery / Kubernetes 调度不纳入一期。

---

## Further Notes

- 现有 Streamlit 入口（`cs_pipeline/app/app.py`）将完整保留在现有路径，所有现有算法验证脚本无需任何路径迁移。
- 数据库连接字符串默认支持环境变量 `DATABASE_URL`，本地开发可缺省连接本地 Docker PostgreSQL，同时兼顾自动化测试下的 SQLite 内存模式。
