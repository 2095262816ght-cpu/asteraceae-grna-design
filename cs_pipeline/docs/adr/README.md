# 架构决策记录（Architecture Decision Records, docs/adr）

> **说明**：本目录收录 `cs_pipeline` 核心模块深度重构的架构决策记录（ADR），遵循标准轻量级 ADR 规范。每个记录包含上下文、决策内容、理由及产生的影响。

---

## 决策记录索引

| 编号与文件 | 标题 | 状态 | 决策核心要点 |
|---|---|---|---|
| [`0001-inference-client-seam.md`](0001-inference-client-seam.md) | 抽象推理客户端缝隙（InferenceClient Seam） | **已实施 (Accepted)** | 解耦 `predict.py` 顶层调度与底层预训练模型/WSL环境执行细节；建立规范的推断客户端缝隙，确保测试注入、优雅降级与确定性行为。 |
| [`0002-candidate-ranking-engine.md`](0002-candidate-ranking-engine.md) | 候选推荐与重排引擎解耦（CandidateRankingEngine） | **已实施 (Accepted)** | 将 gRNA 候选排序从 Streamlit Demo UI (`app/app.py`) 中彻底剥离为独立的领域服务类，统一多组学表达加权、脱靶惩罚与 tie-break 规则。 |
| [`0003-sequence-spec.md`](0003-sequence-spec.md) | 统一序列规范（SequenceSpec） | **已实施 (Accepted)** | 确立 30nt 上下文（4nt + 20nt guide + 3nt PAM + 3nt）、正反链坐标换算与合法字符校验的值对象契约，杜绝 off-by-one 坐标错位与 PAM 颠倒。 |
| [`0004-fullstack-postgres-fastapi-react.md`](0004-fullstack-postgres-fastapi-react.md) | 全栈架构重构：PostgreSQL + FastAPI 异步状态机 + React 现代前端 | **已采纳 (Accepted)** | 确立生产级全栈形态：PostgreSQL 分层存储与任务状态机、FastAPI 异步非阻塞接口、React 19 + ECharts 交互前端，通过 Docker Compose 与双轨共存平滑交付。 |

