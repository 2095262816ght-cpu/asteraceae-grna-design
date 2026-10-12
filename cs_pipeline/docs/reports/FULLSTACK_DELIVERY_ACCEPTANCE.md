# 菊科 CRISPR/Cas9 基因编辑全栈系统生产级交付与双轨验收报告

> **项目名称**: Asteraceae CRISPR/Cas9 gRNA Design & Multi-omics Decision Pipeline (Full-Stack Edition)  
> **交付日期**: 2026-09-26  
> **执行标准**: MATT-POCOCK SPEC-0001 / ADR 0004 / 3-Tier Onion Layout  
> **质量保证**: 全量自动化测试套件（后端 17 项全部通过、前端 13 项全部通过、双轨数值比对 100% 吻合）

---

## 一、系统整体架构 (3-Tier Clean Onion Architecture)

```mermaid
graph TB
    subgraph Frontend [前端现代展示层 (Vite + React 19 + TypeScript)]
        UI[Tailwind CSS + shadcn/ui]
        Map[ECharts 基因组物理双轨图谱]
        QueryClient[TanStack Query 异步轮询 & 缓存]
        Drawer[历史任务滑出式抽屉 & 导出操作栏]
    end

    subgraph Backend [应用服务与 API 层 (FastAPI + Async SQLAlchemy 2.0)]
        Router[API v1 统一路由]
        AuthHealth[系统自检 /api/v1/health]
        CandidateAPI[靶点多维检索 /api/v1/candidates]
        ScoringAPI[单序列与批量异步打分 /api/v1/scoring]
        ExportAPI[实验设计批次与下载 /api/v1/exports]
        TaskPool[BackgroundTasks 异步进程执行池]
    end

    subgraph Persistence [持久化存储引擎 (PostgreSQL 16 / SQLite 本地降级)]
        PG[(PostgreSQL 16 / lifescience.db)]
        GenesTbl[genes 表 - 49 NLR基因]
        CandTbl[target_candidates 表 - 19,839 gRNA]
        JobTbl[scoring_jobs / scoring_job_items 表]
        ExportTbl[export_batches 表]
    end

    subgraph DomainCore [算法内核与生信规则 (cs_pipeline - 纯净零污染)]
        GLMM[分层选择性 Beta-Binomial GLMM v2.1/noB879]
        Spec[SequenceSpec 30bp分子结构解构]
        DeepSp[TensorFlow DeepSpCas9 推理进程]
        CRISPRon[WSL/近似 CRISPRon 推理引擎]
        GroundTruth[Streamlit 原型基准 cs_pipeline/app/app.py]
    end

    Frontend -->|HTTP / JSON / 流式下载| Backend
    Backend -->|Async Engine / aiosqlite / psycopg| Persistence
    Backend -->|进程桥接 / 无侵入依赖| DomainCore
```

---

## 二、7 个垂直切片 (Tickets) 交付全景对照

| Ticket 编号 | 切片核心交付内容 | 对应核心代码与组件 | 验收状态 |
| :--- | :--- | :--- | :--- |
| **Ticket 01** | 全栈脚手架与物理数据库健康自检 | `backend/app/main.py`<br>`frontend/src/components/SystemHealthCard.tsx` | **已完成 (Commit `0da11a6`)** |
| **Ticket 02** | 49 基因与 19,839 候选自动灌库检索 | `backend/app/db/seed.py`<br>`frontend/src/components/CandidateSearchPanel.tsx` | **已完成 (Commit `e88f2d9`)** |
| **Ticket 03** | 基因组靶点物理分布与 ECharts 交互图谱 | `frontend/src/components/GenomicTargetMap.tsx`<br>双链散点、Backbone方向、双向联动选中 | **已完成 (Commit `384bd62`)** |
| **Ticket 04** | 单序列 30bp 实时打分与分子解构持久化 | `backend/app/services/scoring_service.py`<br>`frontend/src/components/SingleScoringCard.tsx` | **已完成 (Commit `8c76982`)** |
| **Ticket 05** | 批量序列上传与异步轮询流水线 | `backend/app/services/batch_service.py`<br>`frontend/src/components/BatchUploadCard.tsx` (1.5s 动态轮询) | **已完成 (Commit `cccfe05`)** |
| **Ticket 06** | 实验设计导出批次与历史任务抽屉 | `backend/app/services/export_service.py`<br>`HistoryDrawer.tsx` / `ExportHistoryPanel.tsx` | **已完成 (Commit `812f4a6`)** |
| **Ticket 07** | 生产级 Docker 编排与双轨一致性验收 | `docker-compose.yml`<br>`run_fullstack.ps1`<br>`test_parity_verification.py` | **已完成 (本提交)** |

---

## 三、双轨数值一致性验收 (Dual-Track Parity Verification)

针对现有 Streamlit 原型（`cs_pipeline/app/app.py` 及底层数据集）与新全栈系统的输出结果，执行了自动化精度比对验收测试（`backend/tests/test_parity_verification.py`）：

### 1. 基因元数据一致性
- **测试结果**: 49 个 NLR 代表基因 100% 吻合。
- **校验字段**: `gene_id`、`chrom`、`start`、`end`、`strand`、`candidate_count` 均与 `cs_pipeline/demo/app_genes.csv` 零误差匹配。

### 2. 候选靶点效率分与推荐排序一致性
- **抽样目标**: `LsaT2T01G023690` 与 `LsaT2T06G019420` 等关键候选基因。
- **比对结果**: API 排序前 10 位的 gRNA 靶位点 ID、链向、PAM 基序、30bp 序列完全一致；
- **生化参数与模型分**:
  - GC 含量 (`gc_pct`): 误差 $< 0.01\%$；
  - 解链温度 (`tm_c`): 误差 $< 0.01^\circ\text{C}$；
  - 终版排序效率分 (`efficiency_score_v21_nob879`): 误差 $< 0.001$；
  - DeepSpCas9 / CRISPRon 模型活性分: 完全等同。

### 3. 自定义 30bp 序列分子结构解构一致性
- **测试样本**: `TTTGTGGATTCCGGTAGAATCTGATGGAAT`、`ATCGGCTAAGCTAGGCTAGCATCGTGGATC` 等。
- **解构结果**: 
  - 5' 上游侧翼区 (4nt): `TTTG` / `ATCG` (100% 一致)
  - 20nt Guide 核心区: `TGGATTCCGGTAGAATCTGA` / `GCTAAGCTAGGCTAGCATCG` (100% 一致)
  - 3nt PAM 基序: `TGG` (100% 一致)
  - 3' 下游侧翼区 (3nt): `AAT` / `ATC` (100% 一致)

---

## 四、全量自动化测试汇总

```text
============================= 后端测试套件 (Pytest) =============================
backend\tests\test_batch_scoring_api.py ....                             [PASS] (4/4)
backend\tests\test_candidates_api.py ..                                  [PASS] (2/2)
backend\tests\test_export_api.py ...                                     [PASS] (3/3)
backend\tests\test_health.py .                                           [PASS] (1/1)
backend\tests\test_parity_verification.py ...                            [PASS] (3/3)
backend\tests\test_seed.py .                                             [PASS] (1/1)
backend\tests\test_single_scoring_api.py ...                             [PASS] (3/3)
总计: 17 passed in 13.03s (100% 通过)

============================= 前端测试套件 (Vitest) =============================
src/components/GenomicTargetMap.test.tsx ..                              [PASS] (2/2)
src/components/SystemHealthCard.test.tsx ..                              [PASS] (2/2)
src/components/HistoryDrawer.test.tsx ..                                 [PASS] (2/2)
src/components/BatchUploadCard.test.tsx ..                               [PASS] (2/2)
src/components/CandidateSearchPanel.test.tsx ..                          [PASS] (2/2)
src/components/ExportHistoryPanel.test.tsx .                             [PASS] (1/1)
src/components/SingleScoringCard.test.tsx ..                             [PASS] (2/2)
总计: 13 passed in 3.32s (100% 通过)

============================= 前端静态打包 (Vite Build) ===========================
✓ 2544 modules transformed.
dist/index.html                     0.45 kB
dist/assets/index-BX_SSQ3T.css     25.54 kB
dist/assets/index-BQxl5HuU.js   1,470.66 kB
✓ built in 1.18s (无任何 TypeScript 或 Linter 错误)
```

---

## 五、环境运行与生产部署指南

### 1. 容器化一键部署 (Docker Compose)
适用于生产服务器或具备 Docker 环境的快速部署：

```powershell
# 在根目录下直接构建并拉起全栈（Postgres + FastAPI + Nginx/React）
docker compose up --build -d

# 查看各容器状态与健康检查
docker compose ps
```
- **前端交互界面**: 访问 `http://localhost` 或 `http://localhost:3000`
- **后端 API 文档**: 访问 `http://localhost:8000/docs`
- **PostgreSQL 16**: 端口 `5432` (数据库 `lifescience`)

### 2. 本地一键启动脚本 (PowerShell)
适用于开发环境或无需 Docker 的单机直接调试：

```powershell
# 运行本地一键拉起脚本（自动检测 Conda、自动建表灌库、并发拉起前后端）
.\run_fullstack.ps1

# 若仅需要执行一次性建表与灌库：
.\run_fullstack.ps1 -SeedOnly
```
- **前端热重载开发服务器**: `http://localhost:5173`
- **后端 FastAPI 服务**: `http://localhost:8000`
- **Swagger API 接口文档**: `http://localhost:8000/docs`

### 3. 原 Streamlit 参照对比运行
现存 Streamlit 原型保持 100% 完整无损伤：

```powershell
# 在 grna-demo 环境内执行（conda activate grna-demo 之后）
python -m streamlit run cs_pipeline/app/app.py
```
访问 `http://localhost:8501` 即可双轨比对验证。
