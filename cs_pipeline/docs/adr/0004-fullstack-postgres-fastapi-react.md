# ADR 0004: 全栈架构重构：PostgreSQL + FastAPI 异步状态机 + React 现代前端

## 状态
Accepted

## 背景与上下文
当前菊科 CRISPR/Cas9 基因编辑设计管线基于 Streamlit（`cs_pipeline/app/app.py`）提供原型交互。随着管线向生产级交付迈进，面临以下关键瓶颈：
1. **状态丢失与无持久化**：用户提交的单序列/批量打分任务、筛选结果与导出清单在页面刷新后即丢失，无法进行历史追溯与协作；
2. **长任务阻塞痛点**：深度学习模型（DeepSpCas9、CRISPRon）推理耗时较长，Streamlit 单线程阻塞执行导致用户界面冻结，缺乏健全的后台排队与进度通知；
3. **数据检索性能局限**：49 个代表基因的候选位点与多组学特征常驻于内存 DataFrame，无法进行高并发 SQL 复杂过滤、范围检索与分页；
4. **前端交互受限**：Streamlit 难以满足基因组位点图谱高密度渲染、动态缩放（DataZoom）及复杂自定义表单交互需求。

## 架构决议
1. **前后端完全解耦与技术栈确立**：
   - **数据库层**：PostgreSQL 16，采用分层存储策略。核心候选靶点数据（`target_candidates`）、打分任务（`scoring_jobs`）与导出批次（`export_batches`）结构化入库并建立 B-Tree 索引；超大只读时相原始矩阵保持为 Parquet/文件。
   - **后端 API 层**：FastAPI，采用 Repository/Adapter 模式无侵入封装 `cs_pipeline/core` 与 `cs_pipeline/app`（尤其是 `InferenceClient` 与 `CandidateRankingEngine`）。
   - **异步执行器**：基于 FastAPI 后台执行器（预留 Task Runner Seam）与 PostgreSQL 任务状态机（`pending` -> `running` -> `completed` / `failed`），支持前端轮询与进度推送。
   - **前端层**：`Vite + React 19 + TypeScript + Tailwind CSS + shadcn/ui`，使用 `TanStack Query` 进行异步数据缓存与轮询，集成 `Apache ECharts` 进行多组学与靶点分布可视化。
2. **双轨演进与平滑交付**：
   - 保留现有 Streamlit 应用（`app.py`）作为黄金基准（Ground Truth）；
   - 提供 `docker-compose.yml` 与 `Alembic` 迁移工具，保障从本地开发到生产容器的一键复现性。

## 收益与权衡 (Trade-offs)
- **收益**：
  - 彻底解决长任务超时冻结问题，支持多任务并行与进度追踪；
  - 候选检索直接走 SQL 索引过滤，显著降低后端内存占用；
  - 专业级的前端交互体验与高扩展性。
- **权衡**：
  - 引入了 PostgreSQL 数据库依赖（通过 Docker Compose 屏蔽配置复杂度）；
  - 系统由单一 Python 脚本转变为多服务架构，需要维护 API 契约与 DB Migration。
