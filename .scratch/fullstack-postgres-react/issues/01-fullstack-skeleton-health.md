# 01: 全栈脚手架与系统健康检查垂直切片

**What to build:** 
搭建全栈工程基础骨架，打通从前端 React 页面到后端 FastAPI 服务再到数据库的最简连通路径。使用者在浏览器打开前端页面后，能够看到一个系统健康监控状态卡片，显示当前后端 API 服务版本、数据库连接状态（PostgreSQL/SQLite 测试会话），确认全栈通信完全畅通。

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] 后端初始化 `backend/` 目录，配置 FastAPI 基础应用、SQLAlchemy 2.0 异步引擎与配置加载
- [x] 后端暴露 `GET /api/v1/health` 检查端点，能够执行 `SELECT 1` 验证数据库会话并返回系统版本与环境状态
- [x] 前端在 `frontend/` 目录完成 Vite + React 19 + TypeScript + Tailwind CSS + shadcn/ui 基础脚手架初始化
- [x] 前端使用 TanStack Query 请求 `/api/v1/health` 并在页面渲染系统健康状态卡片（带正常/异常视觉标识）
- [x] 编写并通过后端 API 端点单元测试（使用 `TestClient`）
- [x] 编写并通过前端组件渲染测试

