# -*- coding: utf-8 -*-
"""b_uncertainty_sensitivity_analysis_0921.py — 针对无锚点批次与大偏移批次的不确定性量化与敏感性分析

针对根问题 3 与暗坑：
  1. 无锚点批次 (USR-5712 61行, USR-17012 4行)：
     不再单点武断置 0，而是基于批次间方差 tau^2 做 50 次 Monte Carlo 多重插补，
     评估模型指标在先验波动下的 95% 置信区间 [rho_2.5%, rho_97.5%]。
  2. USR-6137 (强材料基线偏移):
     在 [0.70, 0.95] 区间扫描物理偏移设定值，量化残差敏感性曲线。
输出:
  - results/b_sensitivity_intervals_0921.csv
  - results/b_usr6137_sensitivity_curve_0921.csv
"""
import os
import sys
import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, LeaveOneGroupOut

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = "data/hitom/hitom_reads_depth_0921.csv"
OUT_INTERVALS = "results/b_sensitivity_intervals_0921.csv"
OUT_CURVE = "results/b_usr6137_sensitivity_curve_0921.csv"

a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_train = set(gid_all[a["处理状态"] == "保留"])

base = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv("results/scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv("results/scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
reads_df = pd.read_csv(READS_CSV)
base = base.merge(reads_df[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

HOMOLOG = {
    "EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
    "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"
}


def prepare_base_data():
    df = base[base.guide_id.isin(pop_train)].copy().reset_index(drop=True)
    df["note"] = df["note"].fillna("")
    df["gc_total"] = df.seq20.map(gc_fraction)
    df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
    df["tm"] = df.seq20.map(Tm_NN)
    df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
    df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
    df["gene_group"] = df["gene_id"].replace(HOMOLOG)

    indel = df["indel_pct"].astype(float)
    shared = df.groupby("seq20")["batch"].nunique()
    shared = set(shared[shared >= 2].index)
    gmed = df[df.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()

    offsets = {}
    anchor_counts = {}
    diff_residuals = []
    for b, sub in df.groupby("batch"):
        s = sub[sub.seq20.isin(shared)]
        anchor_counts[b] = len(s)
        if len(s):
            diff = s["indel_pct"] - s.seq20.map(gmed)
            offsets[b] = diff.median()
            if len(s) > 1:
                diff_residuals.extend(diff - diff.mean())
        else:
            offsets[b] = 0.0

    s2 = np.var(diff_residuals) if diff_residuals else 0.04
    offs_valid = [offsets[b] for b in offsets if anchor_counts.get(b, 0) > 0]
    tau2 = max(1e-4, np.var(offs_valid) - s2 / np.mean([anchor_counts[b] for b in offsets if anchor_counts.get(b, 0) > 0]))

    feats = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]
    X = df[feats].astype(float).values
    groups = df["gene_group"].values
    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    weights = n_reads / np.mean(n_reads)

    return df, indel, offsets, anchor_counts, tau2, X, groups, weights


def evaluate_offsets(df, indel, custom_offsets, X, groups, weights):
    """在指定偏移下运行快速 LOGO 评测"""
    y_target = ((indel - df["batch"].map(custom_offsets).fillna(0.0)).clip(0, 1) * 100.0).values
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y_target, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y_target[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y_target[tr_i], sample_weight=weights[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        y_te = y_target[te_i]
        if len(set(np.round(y_te, 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
            rhos.append(spearmanr(p_i, y_te)[0])
    return float(np.nanmedian(rhos))


def main():
    df, indel, offsets, anchor_counts, tau2, X, groups, weights = prepare_base_data()
    tau = np.sqrt(tau2)
    print(f"估计批次间标准差 tau = {tau:.4f} (方差 tau^2 = {tau2:.4f})")

    # 1. 任务一：USR-6137 连续灵敏度曲线
    print("\n=== 任务一：USR-6137 偏移敏感性曲线 ===")
    curve_records = []
    scan_vals = [0.70, 0.75, 0.80, 0.838, 0.8688, 0.90, 0.95]
    for v in scan_vals:
        curr_offs = offsets.copy()
        curr_offs["USR-6137"] = v
        med_rho = evaluate_offsets(df, indel, curr_offs, X, groups, weights)
        print(f"  USR-6137 offset={v:.4f} -> LOGO med_rho={med_rho:+.4f}")
        curve_records.append({"usr6137_offset": v, "logo_med_rho": round(med_rho, 4)})

    pd.DataFrame(curve_records).to_csv(OUT_CURVE, index=False)
    print(f"已保存 USR-6137 敏感性曲线至 {OUT_CURVE}")

    # 2. 任务二：无锚点批次 (USR-5712, USR-17012) Monte Carlo 多重插补
    print("\n=== 任务二：无锚点批次 50 次 Monte Carlo 多重插补 ===")
    np.random.seed(42)
    mc_rhos = []
    n_sim = 50

    for i in range(n_sim):
        curr_offs = offsets.copy()
        # 从 N(0, tau^2) 抽取扰动偏移
        curr_offs["USR-5712"] = float(np.random.normal(0.0, tau))
        curr_offs["USR-17012"] = float(np.random.normal(0.0, tau))
        med_rho = evaluate_offsets(df, indel, curr_offs, X, groups, weights)
        mc_rhos.append(med_rho)
        if (i + 1) % 10 == 0:
            print(f"  完成 {i+1}/{n_sim} 次插补评估...")

    mc_rhos = np.array(mc_rhos)
    mean_rho = float(np.mean(mc_rhos))
    p2_5 = float(np.percentile(mc_rhos, 2.5))
    p50 = float(np.percentile(mc_rhos, 50.0))
    p97_5 = float(np.percentile(mc_rhos, 97.5))
    std_rho = float(np.std(mc_rhos))

    print("\nMonte Carlo 模拟统计结果:")
    print(f"  期望均值 E[rho] = {mean_rho:+.4f}")
    print(f"  中位数 med[rho] = {p50:+.4f}")
    print(f"  标准差 std[rho] = {std_rho:.4f}")
    print(f"  95% 置信区间: [{p2_5:+.4f}, {p97_5:+.4f}]")

    interval_summary = [{
        "cohort": "train969",
        "method": "Depth_Weighted_Anchor (A2)",
        "zero_anchor_batches": "USR-5712 (61 rows), USR-17012 (4 rows)",
        "n_simulations": n_sim,
        "mean_rho": round(mean_rho, 4),
        "median_rho": round(p50, 4),
        "std_rho": round(std_rho, 4),
        "ci_2.5%": round(p2_5, 4),
        "ci_97.5%": round(p97_5, 4),
    }]
    pd.DataFrame(interval_summary).to_csv(OUT_INTERVALS, index=False)
    print(f"已保存置信区间汇总至 {OUT_INTERVALS}")


if __name__ == "__main__":
    main()
