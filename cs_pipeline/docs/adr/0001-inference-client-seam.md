# ADR 0001: 建立跨环境推理客户端接缝模块 (InferenceClient)

## 状态
Accepted

## 背景与上下文
在当前系统中，`genet` 库（负责 DeepSpCas9 模型推理）锁定了 `tensorflow<2.10` 和 `protobuf<3.20`，而 `streamlit` 需要现代 `protobuf`。为此团队采用了双 Conda 环境策略：`grna-demo` 运行前端，`crispr` 运行模型推理。

然而，跨环境调用的实现直接侵入在 UI 视图（`app/app.py` Tab 2）中：
1. 遍历 10 个候选路径去探测 `crispr` 环境 Python 解释器；
2. 侵入式修改 Windows 的 `PATH` 环境变量（注入 `Library/bin` 以补齐 DLL）；
3. 显式组装 `subprocess.run` 并通过 stdin 写入文本行、通过 stdout 读取 CSV；
4. 解析 CSV 并手动转换 `crispron_source` 字符串枚举。

这种浅接缝带来了严重的架构痛点：
- **Locality 缺失**：环境修复、跨平台路径查找或 IPC 协议调整会波及 UI 表现层；
- **测试成本高昂**：自动化测试必须使用 Streamlit 的 `AppTest` 无头执行 30 秒以上，无法通过纯 Python 测试直接验证跨进程通信与降级逻辑；
- **接口脆弱**：异常捕获与超时兜底逻辑与前端弹窗强耦合。

## 架构决议
1. 建立深度模块 `cs_pipeline/app/inference_client.py`（类名 `InferenceClient`）。
2. 提供极简类型化接口：
   ```python
   client = InferenceClient()
   result = client.score_sequences(sequences: list[str]) -> BatchInferenceResult
   ```
   返回不可变的 `BatchInferenceResult`，包含标准结果 DataFrame、耗时、降级样本数、降级告警信息等。
3. 内部接缝职责完全下沉：
   - 自动推断并缓存 `CRISPR_PYTHON` 解释器路径；
   - 自动配置 Windows DLL 运行环境与环境变量；
   - 负责命令行子进程的组装、调用、stdin/stdout 序列化及超时控制；
   - 解析产物，自动将模型层状态码翻译为业务语义标签；
   - 将底层 `TimeoutExpired`、`FileNotFoundError` 或进程错误统一包装为结构化错误。
4. `app/app.py` 的 Tab 2 仅作为调用方，不再包含任何子进程或环境查找代码。

## 收益与验证
- **Leverage**：UI 减少约 50 行样板代码；
- **Locality**：子进程与跨环境调用全部收拢在单一模块，一处修改到处生效；
- **测试性**：新增轻量级单元测试直接对 `InferenceClient` 接口进行快速断言。
