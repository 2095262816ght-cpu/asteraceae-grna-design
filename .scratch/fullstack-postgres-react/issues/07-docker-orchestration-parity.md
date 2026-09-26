# 07: 生产级 Docker 编排与 Streamlit 双轨交付验收

**What to build:** 
完成全栈生产级交付与数值一致性比对验收。编写根目录 `docker-compose.yml`，一键拉起 PostgreSQL 数据库、FastAPI 后端服务与 Vite/Nginx 前端应用，启动时自动完成数据库初始化与数据灌库。编写自动化验收脚本，对相同基因（如 NLR 代表基因）和相同自定义输入序列，自动化比对 React 前端输出与现有 Streamlit（`cs_pipeline/app/app.py`）计算结果严格一致性，产出最终验收报告。

**Blocked by:** 03: 基因组靶点物理分布与 ECharts 交互图谱切片, 06: 实验设计导出批次与历史任务抽屉切片

**Status:** ready-for-agent

- [ ] 编写根目录 `docker-compose.yml` 与对应的 `backend/Dockerfile`、`frontend/Dockerfile`、`frontend/nginx.conf`
- [ ] 编写一键本地运行脚本 `run_fullstack.ps1`，支持无 Docker 环境下的本地热重载调试
- [ ] 编写容器健康检查与自动启动迁移脚本
- [ ] 编写双轨数值比对验收测试脚本，自动化抽样比对 React API 输出与 Streamlit 原型基准输出（效率分、推荐排序、PAM 解构与降级标签），确认 100% 吻合
- [ ] 产出交付验收文档与用户运行指南
