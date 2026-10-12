# 项目执行方案与分工规范（docs/plans）

> **说明**：本目录收录本项目现行生效的主方案与跨学科分工详案。若不同文档间出现技术口径冲突，遵循以主方案为最高依据的仲裁原则。

---

## 方案文件索引

| 文件 | 角色定位 | 维护者 | 核心内容 |
|---|---|---|---|
| [`project_plan_v3_condensed_0907.md`](project_plan_v3_condensed_0907.md) | **主方案（最高依据）** | 全体成员 | 公开预训练模型（DeepSpCas9 / CRISPRon）+ 自有橡胶草 Hi-TOM 数据 Stacking 集成架构；莴苣 T2T 参考基因组扫描与候选排序验证。与详案冲突时以本文件为准。 |
| [`division_plan_master.md`](division_plan_master.md) | **全员甘特总表与接口规范** | 生D（统筹） | 全队甘特图、跨专业交付接口 F1~F7 权威数据格式契约、风险应对矩阵、终版提交自查表。 |
| [`division_plan_biology.md`](division_plan_biology.md) | **生物系分工详案** | 生A ~ 生D | 逐人逐日任务卡、F1 数据清洗标准 12 列权威定义、引物设计与突变类型标记规范。 |
| [`division_plan_cs.md`](division_plan_cs.md) | **计算机系分工详案** | 计A / 计B | `cs_pipeline/` 目录组织体系、特征提取→Stacking/GLMM模型训练→全基因组扫描→Cas-OFFinder脱靶排查→Streamlit Demo 端到端脚本规范与验收准则。 |
| [`multiomics_implementation_plan.md`](multiomics_implementation_plan.md) | **多组学拓展实施计划** | 计A / 计B | 转录表达数据六大应用方案实施规范（Demo表达看板、消融实验、组织重排、功能性脱靶危害评定等）。实施结果见 [`../reports/multiomics_five_schemes_implementation_report_0924.md`](../reports/multiomics_five_schemes_implementation_report_0924.md)。 |
| [`fullstack_postgres_fastapi_react_spec.md`](fullstack_postgres_fastapi_react_spec.md) | **全栈架构升级规格（SPEC-0001）** | 计A / 计B | PostgreSQL + FastAPI 异步任务 + React 前端的生产级全栈实施规格，对应 [`../adr/0004-fullstack-postgres-fastapi-react.md`](../adr/0004-fullstack-postgres-fastapi-react.md)。交付验收见 [`../reports/FULLSTACK_DELIVERY_ACCEPTANCE.md`](../reports/FULLSTACK_DELIVERY_ACCEPTANCE.md)。 |
