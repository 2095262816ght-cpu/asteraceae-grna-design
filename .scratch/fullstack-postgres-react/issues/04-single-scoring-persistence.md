# 04: 单序列实时打分与结果持久化垂直切片

**What to build:** 
打通单序列实时打分流水线。生信人员在前端界面输入一段 30nt 自定义序列，前端调用后端 `POST /api/v1/scoring/single`。后端调用 `SequenceSpec` 校验序列合法性与解构分子区间，调度 `InferenceClient` 运行模型推理计算出相对排序效率分，并将该任务记录持久化保存至 `scoring_jobs` 数据库表中。前端即时呈现结果卡片，显示预测效率分、GC 含量、解构区间详情及模型来源（如是否触发经验降级）。

**Blocked by:** 01: 全栈脚手架与系统健康检查垂直切片

**Status:** completed

- [x] 在后端建立 `scoring_jobs` 与 `scoring_job_items` 数据库模型与状态字段
- [x] 后端无侵入桥接 `cs_pipeline.core.sequence_spec.validate_seq30` 与 `cs_pipeline.app.inference_client.InferenceClient`
- [x] 后端暴露 `POST /api/v1/scoring/single` 端点，支持同步即时打分并将输入与产物持久化写入数据库
- [x] 前端构建“单序列打分”工作台表单卡片，包含 30nt 长度即时校验与一键填入示例序列按钮
- [x] 前端渲染结果展示卡片，清晰呈现效率分、GC 含量、Tm、解构区段与模型来源标注徽章
- [x] 编写并通过后端单序列打分 API 端到端测试（通过 Stub 隔离耗时模型调用）
- [x] 编写并通过前端表单输入校验与打分结果卡片渲染测试
