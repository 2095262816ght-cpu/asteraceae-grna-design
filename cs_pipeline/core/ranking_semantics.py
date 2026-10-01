# -*- coding: utf-8 -*-
"""ranking_semantics.py — 组织优先指数 (TissuePriorityIndex) 与功能性脱靶危害
(FunctionalOfftargetHazard) 的公式、权重与文案单点定义。

此前权重与公式四处散落：backend multiomics_service（计算）、export_service（方法学
文案）、前端排序帮助文案、cs_pipeline scripts/21–22 与推荐引擎（科研轨计算）——
权重改一处漏三处，文案与实现漂移无人报警。本模块只含纯常量、纯函数与公式文案
（零重依赖），两轨共同消费；跨轨行为一致性由 backend/tests/test_parity_verification.py
与既有回归测试守护。

公式定义（CONTEXT.md §3）：
- PriorityScore = W_EFF×EffPct − W_PEN×Penalty + W_EXPR×S(E_t)   （方案3）
- PriorityScore_ATAC = 0.45×EffPct − 0.25×Penalty + 0.20×S(E_t) + 0.10×Atac（表观折中变体）
- Penalty = min(1, (exact·w0 + mis1·w1 + mis2·w2 + mis3·w3) / PENALTY_CAP)
- S(E) = sigmoid(log2(TPM+1) − SIGMOID_CENTER)；无表达证据 → 0（不加分也不倒扣）
- Hazard_t = Σ ω(mis) × w_t(命中基因)；w_t = 1 + HAZARD_EXPR_COEF×log2(TPM_t+1)，
  不可映射基因取 HAZARD_UNMAPPABLE_WEIGHT（数值越小越安全）
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

# 方案3 权重（0923 修订版）
W_EFF = 0.50
W_PEN = 0.25
W_EXPR = 0.25

# 表观可及性折中变体权重
W_EFF_ATAC = 0.45
W_PEN_ATAC = 0.25
W_EXPR_ATAC = 0.20
W_ATAC = 0.10

# Penalty 错配计数权重（exact, mis1, mis2, mis3）与归一上限
MIS_WEIGHTS = (1.0, 0.5, 0.2, 0.05)
PENALTY_CAP = 10.0

# 表达 sigmoid 中心
SIGMOID_CENTER = 2.0

# 功能性脱靶危害（方案5）
HAZARD_OMEGA = {0: 10.0, 1: 3.0, 2: 1.0, 3: 0.2}
HAZARD_EXPR_COEF = 0.5
HAZARD_UNMAPPABLE_WEIGHT = 0.1


def expression_term(tpm: Optional[float]) -> float:
    """S(E) = sigmoid(log2(TPM+1) − SIGMOID_CENTER)；无表达证据 → 0。"""
    if tpm is None:
        return 0.0
    e = math.log2(max(float(tpm), 0.0) + 1.0)
    return 1.0 / (1.0 + math.exp(-(e - SIGMOID_CENTER)))


def penalty(exact, mis1, mis2, mis3):
    """Penalty = min(1, Σ mis权重×计数 / PENALTY_CAP)。标量输入。"""
    raw = (
        exact * MIS_WEIGHTS[0]
        + mis1 * MIS_WEIGHTS[1]
        + mis2 * MIS_WEIGHTS[2]
        + mis3 * MIS_WEIGHTS[3]
    ) / PENALTY_CAP
    return min(1.0, raw)


def priority_score(pct, penalty_value, expr_term):
    """PriorityScore = W_EFF×Pct − W_PEN×Penalty + W_EXPR×S(E)。

    纯算术式：pct/penalty/expr_term 传标量或 pandas Series 均可（向量化同式）。
    """
    return W_EFF * pct - W_PEN * penalty_value + W_EXPR * expr_term


def priority_score_atac(pct, penalty_value, expr_term, atac):
    """表观折中变体：0.45×Pct − 0.25×Penalty + 0.20×S(E) + 0.10×Atac。"""
    return W_EFF_ATAC * pct - W_PEN_ATAC * penalty_value + W_EXPR_ATAC * expr_term + W_ATAC * atac


def hazard_gene_weight(tpm: Optional[float]) -> float:
    """危害权重 w_t = 1 + HAZARD_EXPR_COEF×log2(TPM_t+1)；不可映射/缺失 → 常数。"""
    if tpm is None:
        return HAZARD_UNMAPPABLE_WEIGHT
    return 1.0 + HAZARD_EXPR_COEF * math.log2(max(float(tpm), 0.0) + 1.0)


def within_gene_percentiles(rows: Sequence) -> Dict[int, float]:
    """基因内效率百分位：rank(pct=True) 于该基因全部候选。

    rows: [(gene_id, id, efficiency_score)]。返回 {id: percentile}。
    此前以 multiomics_service._within_gene_percentiles 私有名被三个模块跨模块引用，
    现为声明接口（贴入集合百分位、导出百分位、注释百分位共用同一口径）。
    """
    import pandas as pd

    df = pd.DataFrame(rows, columns=["gene_id", "id", "efficiency_score"]).dropna(
        subset=["efficiency_score"]
    )
    df["pct"] = df.groupby("gene_id")["efficiency_score"].rank(pct=True)
    return {int(i): float(p) for i, p in zip(df["id"], df["pct"])}


# ---- 公式文案（导出方法学说明 / 前端排序帮助共用，数字取自上方常量，不得漂移） ----

def priority_formula_text() -> str:
    return (
        f"PriorityScore = {W_EFF}×效率百分位 − {W_PEN}×Penalty + {W_EXPR}×S(E_t)；"
        f"效率百分位 = 同基因全部候选内按综合排序效率分排名的百分位；"
        f"Penalty = min(1, (exact×{MIS_WEIGHTS[0]} + mis1×{MIS_WEIGHTS[1]}"
        f" + mis2×{MIS_WEIGHTS[2]} + mis3×{MIS_WEIGHTS[3]})/{PENALTY_CAP:g})；"
        f"S(E) = sigmoid(log2(TPM_t+1) − {SIGMOID_CENTER:.1f})"
    )


def priority_atac_formula_text() -> str:
    return (
        f"PriorityScore_ATAC = {W_EFF_ATAC}×效率百分位 − {W_PEN_ATAC}×Penalty"
        f" + {W_EXPR_ATAC}×S(E_t) + {W_ATAC}×ATAC可及性分（表观折中变体）"
    )


def hazard_formula_text() -> str:
    omega = ", ".join(f"{k}:{v:g}" for k, v in sorted(HAZARD_OMEGA.items()))
    return (
        f"Hazard_t = Σ ω(错配数) × w_t(命中基因)；ω = {{{omega}}}；"
        f"w_t = 1 + {HAZARD_EXPR_COEF:g}×log2(TPM_t+1)（命中基因不可映射时取 {HAZARD_UNMAPPABLE_WEIGHT:g}）"
    )
