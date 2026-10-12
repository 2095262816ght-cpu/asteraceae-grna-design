# -*- coding: utf-8 -*-
"""21_build_tissue_priority_recommendations.py — 方案3：组织特异多组学优先指数全候选重排

对 demo 全部候选 gRNA，在「序列效率分百分位 − 脱靶危害惩罚 ＋ 目标组织表达激活」三项目标下
计算综合推荐指数，并按 5 种目标组织分别生成排序列，落盘 demo/app_data_tissue_priority.csv。

数学模型（方案文档 0923 修订版）：
    PriorityScore(i, t) = 0.50 * Percentile(EffScore_i)
                        - 0.25 * Penalty(OffTarget_i)
                        + 0.25 * S(E_t(g))
    S(E) = 1 / (1 + exp(-(E - 2.0)))            # E = log2(TPM+1)，饱和值 1.0
    Penalty = min(1, (mis0*1.0 + mis1*0.5 + mis2*0.2 + mis3*0.05) / 10)

口径（0923）：
- EffScore 取 efficiency_score_v21_nob879（现行 v2.1 生产列）；百分位在全部候选内计算，
  使分数跨基因可比（方案3 的目标即“全基因候选重排”）。
- 表达项经 scripts/16 crosswalk 映射到 LSA 后取 5 组织 TPM；
  **不可映射基因（crosswalk tier4）表达项记 0（无证据即无加分）并以 expression_status 标注**，
  不伪造表达值；前端据此提示“表达证据缺失”而非“转录静默”。

运行：python scripts/21_build_tissue_priority_recommendations.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
# 公式与权重单点定义在 core.ranking_semantics（与 backend、demo 引擎同源）
from core.ranking_semantics import (  # noqa: E402
    MIS_WEIGHTS,
    PENALTY_CAP,
    SIGMOID_CENTER,
    priority_score,
)

APP_DATA = BASE_DIR / "demo" / "app_data.csv"
XWALK = BASE_DIR / "results" / "crosswalk_lsa_t2t_0923.csv"
EXPR = BASE_DIR / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"
OUT = BASE_DIR / "demo" / "app_data_tissue_priority.csv"

TISSUES = ["Root", "Stem", "Leaf", "Flower", "Seed"]
EFF_COL = "efficiency_score_v21_nob879"


def main():
    df = pd.read_csv(APP_DATA)
    xw = pd.read_csv(XWALK).set_index("gene_id")
    expr = pd.read_csv(EXPR).set_index("GeneID")
    assert EFF_COL in df.columns and df[EFF_COL].notna().all(), "缺少 v2.1 效率分列"
    missing = set(df.gene_id) - set(xw.index)
    assert not missing, f"crosswalk 缺少基因: {sorted(missing)}"

    row = df.gene_id.map(xw["lsa_primary"])
    df["lsa_id"] = row
    mapped = row.notna()

    status = np.where(~mapped, "unmappable",
                      np.where(xw.reindex(df.gene_id)["scaffold_evidence"].notna(),
                               "mapped_scaffold",
                               np.where(xw.reindex(df.gene_id)["n_cluster"] > 1,
                                        "mapped_cluster", "mapped")))
    df["expression_status"] = status

    # 表达激活项 S(E_t)；不可映射记 0（无证据即无加分）
    for t in TISSUES:
        tpm = pd.Series(np.nan, index=df.index, dtype=float)
        have = mapped & row.isin(expr.index)
        tpm[have] = expr.loc[row[have], t].astype(float).values
        e = np.log2(tpm.clip(lower=0) + 1.0)
        df[f"expr_sigmoid_{t.lower()}"] = np.where(
            have, 1.0 / (1.0 + np.exp(-(e - SIGMOID_CENTER))), 0.0)

    pct = df[EFF_COL].rank(pct=True)
    pen = np.minimum(
        1.0,
        (df["exact_match_count"] * MIS_WEIGHTS[0]
         + df["offtarget_count_mis1"] * MIS_WEIGHTS[1]
         + df["offtarget_count_mis2"] * MIS_WEIGHTS[2]
         + df["offtarget_count_mis3"] * MIS_WEIGHTS[3]) / PENALTY_CAP)
    df["eff_percentile"] = pct.round(6)
    df["offtarget_penalty"] = pen.round(6)

    for t in TISSUES:
        score = priority_score(pct, pen, df[f"expr_sigmoid_{t.lower()}"])
        tl = t.lower()
        df[f"priority_score_{tl}"] = score.round(6)
        df[f"priority_rank_{tl}"] = score.rank(ascending=False, method="first").astype(int)

    df.to_csv(OUT, index=False)

    print(f"候选 {len(df)} 条 / 基因 {df.gene_id.nunique()} 个 -> {OUT}")
    print("expression_status 分布:", df.expression_status.value_counts().to_dict())
    leaf = df.sort_values("priority_rank_leaf")
    eff = df.sort_values(EFF_COL, ascending=False)
    top = 50
    overlap = set(leaf.head(top).guide_id) & set(eff.head(top).guide_id)
    print(f"Leaf 优先指数 top{top} 与纯效率分 top{top} 重叠 {len(overlap)} 条"
          f"（重排实际改变了推荐集合）")
    unm = df[df.expression_status == "unmappable"]
    if len(unm):
        print(f"不可映射基因 {unm.gene_id.nunique()} 个 / {len(unm)} 条候选："
              f"表达项记 0，前端标注“表达证据缺失”")
    print("\nLeaf top 10 预览：")
    print(leaf.head(10)[["guide_id", "gene_id", "lsa_id", EFF_COL,
                         "offtarget_penalty", "expr_sigmoid_leaf",
                         "priority_score_leaf"]].to_string(index=False))


if __name__ == "__main__":
    main()
