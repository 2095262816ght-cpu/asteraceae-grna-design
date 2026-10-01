# -*- coding: utf-8 -*-
"""crispron_scorer.py — CRISPRon 打分来源裁决模块（`crispron_source` 不变量的唯一执行点）。

不变量：**近似值必须逐条标注为 `approximated`，绝不冒充 `wsl_real` 真实模型输出。**
此前该策略由调用方各自承担——predict.py 与 scripts/26 各持一份近似式副本
（`deep*0.95 + (tm-50)*0.25`）和标注决策，scripts/29 再手写标签字面量，任何一处
漏标都会把降级值当真值展示（历史 P0「推理期特征伪造」正是这样发生的）。

接口（调用方只需要知道这一件事）：
    CrispronScorer(real_runner).score(seqs, deep, tm) -> DataFrame[crispron_score, crispron_source]

实现隐藏两个适配器：
- 真实模型适配器 `real_runner: callable(seqs) -> {seq30: 分}`，默认懒绑定
  `scripts.crispron_wsl.score`（WSL/native 实跑，见 ADR-0001 相邻接缝）；
- 标注降级适配器（内部近似式），对真实模型不可用或无精确 30mer 匹配的行逐条接管。

`no_real_runner` 是批量预计算口径的具名适配器：全量 1e7 级规模不实跑真实模型，
全部走近似式并标注 `approximated`（scripts/26 的既定口径，前端必须如实展示）。
"""
from __future__ import annotations

import pandas as pd

SOURCE_WSL_REAL = "wsl_real"
SOURCE_APPROXIMATED = "approximated"
COLUMNS = ["crispron_score", "crispron_source"]

# 经验近似式（降级适配器）：approx = deep×0.95 + (Tm−50)×0.25
APPROX_DEEP_WEIGHT = 0.95
APPROX_TM_CENTER = 50.0
APPROX_TM_WEIGHT = 0.25


def approx_formula_text() -> str:
    """近似式文案（导出方法学说明共用，数字与实现同源不得漂移）。"""
    return f"deepspcas9×{APPROX_DEEP_WEIGHT}+(Tm−{APPROX_TM_CENTER:g})×{APPROX_TM_WEIGHT}"


def _default_runner():
    # 懒绑定：本模块仅依赖 pandas，测试与纯计算路径不拉起 WSL/TF 栈
    try:
        from . import crispron_wsl
    except ImportError:
        import crispron_wsl
    return crispron_wsl.score


def no_real_runner(_seqs):
    """批量预计算口径：不实跑真实模型，全部降级并标注。"""
    return {}


class CrispronScorer:
    """CRISPRon 来源裁决：真实模型优先，逐条降级标注。"""

    def __init__(self, real_runner=None):
        self._real = real_runner

    def score(self, seqs, deep_scores, tm_values) -> pd.DataFrame:
        """返回与 deep_scores 同索引的 DataFrame[crispron_score, crispron_source]。

        seqs: seq30 列表；deep_scores/tm_values: 经验近似式所需的派生特征（pd.Series）。
        """
        index = deep_scores.index
        if len(index) == 0:
            return pd.DataFrame(columns=COLUMNS, index=index)

        real = (self._real if self._real is not None else _default_runner())(
            [str(s).upper().strip() for s in seqs]
        )
        real_vals = pd.Series(
            [real.get(str(s).upper().strip(), float("nan")) for s in seqs],
            index=index,
            dtype=float,
        )
        approx = (
            deep_scores.astype(float) * APPROX_DEEP_WEIGHT
            + (tm_values.astype(float) - APPROX_TM_CENTER) * APPROX_TM_WEIGHT
        ).round(2)
        is_real = real_vals.notna()
        return pd.DataFrame(
            {
                "crispron_score": real_vals.fillna(approx),
                "crispron_source": is_real.map({True: SOURCE_WSL_REAL, False: SOURCE_APPROXIMATED}),
            },
            index=index,
        )
