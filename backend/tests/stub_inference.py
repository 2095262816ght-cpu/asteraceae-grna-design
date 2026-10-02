"""InferenceClient 测试替身：预置模型分行，走与真实推理相同的消费接口。

口径：测试不依赖真实模型环境（WSL/容器）是否可用，两条路径都确定性覆盖——
有模型分（替身注入）与无模型分（如实标缺失）。
"""
import pandas as pd


class StubInferenceResult:
    def __init__(self, rows: list):
        self.raw_df = pd.DataFrame(rows)
        self.has_approximated = False
        self.warning_message = None


class StubInferenceClient:
    """接口同 InferenceClient.score_sequences：按传入序列顺序返回预置分行。"""

    def __init__(self, rows: list):
        self._rows = rows

    def score_sequences(self, seqs, timeout_s=None):
        return StubInferenceResult(self._rows[: len(seqs)])
