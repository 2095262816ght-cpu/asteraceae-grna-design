# -*- coding: utf-8 -*-
"""25_sensitivity_dual_grna_0924.py — 双 gRNA 块 38 行的剔除敏感性分析（P1b 的低成本前置）。

为什么先做这个而不是直接做 -A/-B 拆分
------------------------------------
完整的切点归属拆分需要裁定 4 条规则（归属窗口、双切读段、远离两切点的变异、-A/-B 行的 rep），
且要把方法从 refsm1 扩到另外 2 个 ref。但真正需要回答的问题不是"怎么拆"，而是
**"对外的两个核心 LOGO 数字扛不扛得住这 38 行"**。这个问题可以用整体剔除来界定，
不需要任何归属规则——与 `results/b_sensitivity_logo_0919.csv` 的既有做法一致。

为什么这 38 行值得单独查
------------------------
它们集中在 3 个基因组（LG05.1856 / LG05.2111 / LG05.2725），而这 3 个基因组占 noB879
的 361 行（41.1%）。更关键的是：**两个对外核心数字都是中位数，而它们的"中位数决定折"
恰好都落在这里**——全折中位 ρ=+0.3635 就是 LG05.2725 那一折的值，Class A 中位 ρ=+0.4636
就是 LG05.1856 那一折的值。中位数对中间观测最敏感：LG05.2725 的 ρ 只要变动约 0.10，
全折中位就会阶跃到邻折的 0.2204 或 0.4636，而不是渐变。

读段级证据（`data/raw/hitom/NEWdata_0918/02_HiTOM结果表格/USR-6883-SY3382/`，块 063-refsm1）
已证实其中一行存在归属错误：TKS_1313 表记 indel_pct=0.9090 归给 guide A
（GGCGTTAGATTGACAGAAGA，备注"guide确定"），但按 WT 读段定位切点后，A 的切点 ±5bp 内
**零切割**，而 84.65% 的读段切在候选 guide B（GTAGCCGGCGGCATCTATAT）的位点上。
同一文件另证实 `indel_pct` 的定义就是"非 WT 读段占比"（4 个块对到小数点后 4 位）。

本脚本做什么
------------
在 full（879 行）与 reduced（剔除 38 行后 841 行）两个队列上，各自完整重跑
`hier_bb_model` 的批次先验 + scripts/15 同款测试集划分 + 16 折 LOGO，逐折对比。
批次先验一并重算：剔除行会改变跨批次共享 seq20 的锚点计数，进而改变 u_prior，
这正是需要量化的传导路径之一。

自检：full 队列的四项指标必须与 `results/metrics_hier_bb_nob879_0921.csv` 逐项一致，
否则本脚本与生产训练不同源，对比无意义。

运行（在 cs_pipeline/ 下，crispr 环境，约 20 秒）：
    python scripts/25_sensitivity_dual_grna_0924.py
产物：
    results/sensitivity_dual_grna_summary_0924.csv   两队列核心指标对比
    results/sensitivity_dual_grna_folds_0924.csv     逐折 ρ 对比（含行数变化与 Class A/B）
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from features_common import FEATURE_COLS, XLSX_161, load_cohort
from hier_bb_model import compute_batch_prior, fit_hierarchical_selective_bb

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_SUMMARY = BASE_DIR / "results" / "sensitivity_dual_grna_summary_0924.csv"
OUT_FOLDS = BASE_DIR / "results" / "sensitivity_dual_grna_folds_0924.csv"
METRICS_CSV = BASE_DIR / "results" / "metrics_hier_bb_nob879_0921.csv"

MARKER = "双gRNA块拆分待执行"
PRIOR_SCALE = 5.0
RANDOM_STATE = 42          # 与 scripts/15 一致
TEST_SIZE = 0.2            # 与 scripts/15 一致
CLASS_A_MIN_BATCHES = 3    # 与 scripts/15 一致
VAR_NDIGITS = 6            # 折内取值多样性判定，与 scripts/15 一致
RHO_NDIGITS = 4            # ρ 落盘精度，与 scripts/15 一致

EXPECTED_FULL = 879
EXPECTED_DROPPED = 38


def dual_grna_guide_ids():
    """主表 `判定依据` 列带双 gRNA 标记的 guide-id 集合（全表口径，稍后与队列求交）。"""
    a = pd.read_excel(XLSX_161, sheet_name="全部打分")
    marked = a["判定依据"].astype(str).str.contains(MARKER, na=False)
    return set(a["guide-id"].astype(str)[marked])


def has_variance(v) -> bool:
    return len(set(np.round(np.asarray(v, dtype=float), VAR_NDIGITS))) > 1


def evaluate(df, tag):
    """在给定队列上完整复刻 scripts/15 的评估，返回 (summary dict, folds DataFrame)。"""
    prior = compute_batch_prior(df)
    X = df[FEATURE_COLS].astype(float).values
    groups = df["gene_group"].values
    indel = df["indel_pct"].astype(float)
    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

    ct = pd.crosstab(df["batch"], df["gene_group"])
    class_a = {g for g in ct.columns if len(ct[g][ct[g] > 0]) >= CLASS_A_MIN_BATCHES}

    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE,
                                    random_state=RANDOM_STATE).split(X, indel, groups))
    b0, w, mu, sd, _ = fit_hierarchical_selective_bb(
        X[tr], n_reads[tr], k_reads[tr], prior["batch_idx"][tr], prior["n_batches"],
        prior["u_prior"], prior["u_prec"], prior["logit_p0"], prior_scale=PRIOR_SCALE)
    pred = b0 + np.dot((X[te] - mu) / sd, w)
    y = indel.values[te]
    test_rho = float(spearmanr(pred, y).correlation) \
        if has_variance(y) and has_variance(pred) else float("nan")

    rows = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, indel, groups):
        grp = groups[te_i][0]
        b0i, wi, mui, sdi, _ = fit_hierarchical_selective_bb(
            X[tr_i], n_reads[tr_i], k_reads[tr_i], prior["batch_idx"][tr_i],
            prior["n_batches"], prior["u_prior"], prior["u_prec"], prior["logit_p0"],
            prior_scale=PRIOR_SCALE)
        pi = b0i + np.dot((X[te_i] - mui) / sdi, wi)
        yi = indel.values[te_i]
        valid = has_variance(yi) and has_variance(pi)
        rows.append({
            "cohort": tag,
            "gene_group": grp,
            "n_samples": len(te_i),
            "n_batches": int((ct[grp] > 0).sum()),
            "class": "Class A" if grp in class_a else "Class B",
            "valid": valid,
            "rho": round(float(spearmanr(pi, yi).correlation), RHO_NDIGITS) if valid else np.nan,
        })
    folds = pd.DataFrame(rows)
    v = folds[folds.valid]
    a = v[v["class"] == "Class A"]
    summary = {
        "cohort": tag,
        "n_rows": len(df),
        "n_gene_groups": int(df["gene_group"].nunique()),
        "n_distinct_seq30": int(df["seq30"].nunique()),
        "test_rho": round(test_rho, RHO_NDIGITS),
        "logo_median_rho": round(float(v["rho"].median()), RHO_NDIGITS),
        "class_a_median_rho": round(float(a["rho"].median()), RHO_NDIGITS) if len(a) else np.nan,
        "class_a_valid_folds": int(len(a)),
        "valid_folds": "%d/%d" % (len(v), len(folds)),
    }
    return summary, folds


def main():
    full = load_cohort("noB879")
    marked = dual_grna_guide_ids()
    dropped = full[full.guide_id.isin(marked)]
    reduced = full[~full.guide_id.isin(marked)].reset_index(drop=True)

    assert len(full) == EXPECTED_FULL, f"noB879 期望 {EXPECTED_FULL} 行，实际 {len(full)}"
    assert len(dropped) == EXPECTED_DROPPED, \
        f"双 gRNA 标记行期望 {EXPECTED_DROPPED} 行，实际 {len(dropped)}"
    assert len(reduced) == EXPECTED_FULL - EXPECTED_DROPPED

    print("[1/4] 队列：full %d 行 / %d 基因组；剔除 %d 行后 reduced %d 行 / %d 基因组"
          % (len(full), full.gene_group.nunique(), len(dropped),
             len(reduced), reduced.gene_group.nunique()))
    per = dropped.groupby("gene_group").size()
    for g, n in per.items():
        print("      %-28s 剔除 %2d 行（%d → %d）"
              % (g, n, int((full.gene_group == g).sum()), int((reduced.gene_group == g).sum())))

    print("[2/4] 评估 full …")
    s_full, f_full = evaluate(full, "full_879")
    print("[3/4] 评估 reduced …")
    s_red, f_red = evaluate(reduced, "reduced_841")

    # 自检：full 必须复现生产指标，否则本脚本与生产训练不同源
    prod = pd.read_csv(METRICS_CSV).iloc[0]
    assert s_full["test_rho"] == round(float(prod["test_rho"]), RHO_NDIGITS), \
        f"full 测试集 ρ {s_full['test_rho']} != 生产 {prod['test_rho']}"
    assert s_full["logo_median_rho"] == round(float(prod["logo_cv_median_rho"]), RHO_NDIGITS), \
        f"full 全折中位 {s_full['logo_median_rho']} != 生产 {prod['logo_cv_median_rho']}"
    assert s_full["class_a_median_rho"] == round(float(prod["class_a_median_rho"]), RHO_NDIGITS), \
        f"full Class A 中位 {s_full['class_a_median_rho']} != 生产 {prod['class_a_median_rho']}"
    assert s_full["valid_folds"] == str(prod["valid_folds"]), \
        f"full 有效折 {s_full['valid_folds']} != 生产 {prod['valid_folds']}"
    print("      自检通过：full 队列四项指标与 metrics_hier_bb_nob879_0921.csv 逐项一致")

    summary = pd.DataFrame([s_full, s_red])
    summary.to_csv(OUT_SUMMARY, index=False)

    merged = f_full.merge(f_red, on="gene_group", how="outer", suffixes=("_full", "_reduced"))
    merged["rho_delta"] = (merged["rho_reduced"] - merged["rho_full"]).round(RHO_NDIGITS)
    merged["n_delta"] = merged["n_samples_reduced"] - merged["n_samples_full"]
    cols = ["gene_group", "class_full", "class_reduced", "n_samples_full", "n_samples_reduced",
            "n_delta", "valid_full", "valid_reduced", "rho_full", "rho_reduced", "rho_delta"]
    merged = merged[[c for c in cols if c in merged.columns]]
    merged.sort_values("gene_group").to_csv(OUT_FOLDS, index=False)

    print("[4/4] 对比")
    print(summary.to_string(index=False))
    print()
    ch = merged[(merged.rho_delta.abs() > 0) | (merged.valid_full != merged.valid_reduced)
                | (merged.class_full != merged.class_reduced)]
    if len(ch):
        print("发生变化的折：")
        print(ch.to_string(index=False))
    else:
        print("无任何折发生变化")
    print()
    for k in ("test_rho", "logo_median_rho", "class_a_median_rho"):
        d = s_red[k] - s_full[k]
        print("  %-20s %+.4f → %+.4f  (Δ%+.4f)" % (k, s_full[k], s_red[k], d))
    print("\n已落盘 %s / %s" % (OUT_SUMMARY.name, OUT_FOLDS.name))


if __name__ == "__main__":
    main()
