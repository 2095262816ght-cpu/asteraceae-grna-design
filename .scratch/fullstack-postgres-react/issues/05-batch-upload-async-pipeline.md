# 05: 批量序列上传与异步轮询流水线切片

**What to build:** 
实现支持百条以上序列的批量预测流水线与异步进度轮询。用户在前端拖拽上传 CSV/Excel 文件（自动检测序列列与 ID 列），前端调用 `POST /api/v1/scoring/upload` 创建异步打分任务。后端立即返回 `job_id` 并在后台任务池中批量执行计算，实时更新任务状态机（`pending` -> `running` -> `completed` / `failed`）与处理进度条。前端使用 TanStack Query 开启 1.5s 动态轮询，展示优雅的进度条动画；计算完成后自动展现批量打分结果列表并支持错误重试。

**Blocked by:** 04: 单序列实时打分与结果持久化垂直切片

**Status:** completed

- [x] 后端构建抽象 `TaskRunner` 执行器，基于 Python 进程池与独立数据库会话管理长任务执行
- [x] 后端暴露 `POST /api/v1/scoring/upload`（支持 CSV/Excel 解析）与 `GET /api/v1/scoring/jobs/{id}`（查询状态与进度）
- [x] 任务执行过程实时更新已处理条数与耗时，捕获异常并记录结构化错误日志
- [x] 前端实现文件拖拽上传组件，支持下载标准导入模板 CSV/Excel
- [x] 前端集成 TanStack Query 动态轮询，渲染任务状态卡片、动态百分比进度条与完成态提示
- [x] 编写并通过异步状态机流转与多序列并发批处理测试
- [x] 编写并通过前端文件上传与轮询进度组件交互测试
