# -*- coding: utf-8 -*-
"""b_identifiability_and_stratified_logo_0921.py — 识别性诊断与混杂感知分层评估

功能：
  1. 计算 21 批次 × 17 基因组列联表与混杂度评分（批次香农熵、跨批数）。
  2. 将 12 个有效 LOGO 折分类为：
     - Class A (低混杂多批折, 跨批数 >= 3, 8个基因): 评估真实生物学序列泛化能力上限
     - Class B (高混杂孤岛折, 跨批数 <= 2, 4个基因): 评估批次绑定下的下限
  3. 分层评估 4 大核心模型：
     - Raw (基准)
     - Anchor (中位数基线)
     - Depth-Weighted Anchor (Method A2)
     - Hierarchical Selective Beta-Binomial (形态二)
输出:
  - results/b_confounding_matrix_0921.csv (21 批次 x 17 基因分布)
  - results/b_confounding_stratified_logo_0921.csv (全量、Class A、Class B 分层指标表)
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b_hierarchical_selective_bb_0921 import (
    build_cohort_data, feats, fit_hierarchical_selective_bb
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = "data/hitom/hitom_reads_depth_0921.csv"
OUT_MATRIX = "results/b_confounding_matrix_0921.csv"
OUT_SUMMARY = "results/b_confounding_stratified_logo_0921.csv"

# 1. 载入人群
a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_train = set(gid_all[a["处理状态"] == "保留"])
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])
pop_ruling = set(gid_all[a["9.19裁决"] == "保留"])

# 2. 基础特征与深度
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


def analyze_confounding(df):
    """构建混杂列联表并计算基因跨批次熵与分类"""
    ct = pd.crosstab(df["batch"], df["gene_group"])
    ct.to_csv(OUT_MATRIX)
    print(f"混杂列联表已保存至 {OUT_MATRIX} (维度: {ct.shape})")

    # 计算每个基因的批次数与香农熵
    gene_stats = []
    for g in ct.columns:
        counts = ct[g][ct[g] > 0]
        n_batches = len(counts)
        total_g = counts.sum()
        probs = counts / total_g
        entropy = -np.sum(probs * np.log2(probs))
        # 分类逻辑: 跨批数 >= 3 为 Class A (低混杂/多批折); <= 2 为 Class B (高混杂/孤岛折)
        strat_class = "Class A (Low-Confounding, Multi-Batch)" if n_batches >= 3 else "Class B (High-Confounding, 1-2 Batches)"
        gene_stats.append({
            "gene_group": g,
            "n_rows": total_g,
            "n_batches": n_batches,
            "entropy": round(entropy, 3),
            "class": strat_class
        })

    stat_df = pd.DataFrame(gene_stats).sort_values("n_batches", ascending=False)
    print("\n基因混杂度分层:")
    print(stat_df.to_string(index=False))
    return {r["gene_group"]: r["class"] for _, r in stat_df.iterrows()}


def run_stratified_bench(pop_name, gids, gene_class_map):
    df_sub = base[base.guide_id.isin(gids)].copy()
    df_sub, y_raw, y_anchor, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, p0, logit_p0 = build_cohort_data(df_sub)
    X = df_sub[feats(df_sub)].astype(float).values
    groups = df_sub["gene_group"].values
    depth_w = n_reads / np.mean(n_reads)

    # 模型列表与评估收集
    models = ["raw", "anchor", "depth_weighted_anchor", "hier_sel_bb_s5.0"]
    fold_rhos = {m: [] for m in models}

    print(f"\n==================== 执行分层 LOGO: {pop_name} (n={len(df_sub)}) ====================")

    for tr_i, te_i in LeaveOneGroupOut().split(X, y_anchor, groups):
        grp = groups[te_i][0]
        y_eval = y_anchor[te_i]
        grp_class = gene_class_map.get(grp, "Unknown")

        # 1. Raw
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y_raw[tr_i], groups[tr_i]))
        g_raw = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_raw.fit(X[tr_i], y_raw[tr_i])
        p_raw = g_raw.best_estimator_.predict(X[te_i])

        # 2. Anchor
        g_anc = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_anc.fit(X[tr_i], y_anchor[tr_i])
        p_anc = g_anc.best_estimator_.predict(X[te_i])

        # 3. Depth-Weighted Anchor
        g_dw = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_dw.fit(X[tr_i], y_anchor[tr_i], sample_weight=depth_w[tr_i])
        p_dw = g_dw.best_estimator_.predict(X[te_i])

        # 4. Form 2: Hierarchical Selective BB
        b0_i, w_i, mu_i, std_i = fit_hierarchical_selective_bb(
            X[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i], n_batches,
            u_prior, u_prec, logit_p0, prior_scale=5.0
        )
        p_bb = b0_i + np.dot((X[te_i] - mu_i) / std_i, w_i)

        # 守卫验证并记录
        if len(set(np.round(y_eval, 6))) > 1:
            for m_name, preds in [("raw", p_raw), ("anchor", p_anc), ("depth_weighted_anchor", p_dw), ("hier_sel_bb_s5.0", p_bb)]:
                if len(set(np.round(preds, 6))) > 1:
                    r = spearmanr(preds, y_eval)[0]
                    fold_rhos[m_name].append({
                        "gene_group": grp,
                        "class": grp_class,
                        "rho": r
                    })

    # 分层汇总
    summary_rows = []
    for m in models:
        m_df = pd.DataFrame(fold_rhos[m])
        all_med = float(m_df["rho"].median()) if len(m_df) else np.nan
        class_a = m_df[m_df["class"].str.startswith("Class A")]
        class_b = m_df[m_df["class"].str.startswith("Class B")]

        med_a = float(class_a["rho"].median()) if len(class_a) else np.nan
        med_b = float(class_b["rho"].median()) if len(class_b) else np.nan

        summary_rows.append({
            "population": pop_name,
            "method": m,
            "all_folds": len(m_df),
            "all_med_rho": round(all_med, 4),
            "class_a_folds": len(class_a),
            "class_a_med_rho (Low-Confounding)": round(med_a, 4),
            "class_b_folds": len(class_b),
            "class_b_med_rho (High-Confounding)": round(med_b, 4),
        })

    return summary_rows


def main():
    # 诊断 train969 上的混杂度
    df_train = base[base.guide_id.isin(pop_train)].copy()
    df_train["gene_group"] = df_train["gene_id"].replace(HOMOLOG)
    gene_class_map = analyze_confounding(df_train)

    all_res = []
    for pop_name, gids in [("train969", pop_train), ("noB879", pop_noB)]:
        res = run_stratified_bench(pop_name, gids, gene_class_map)
        all_res.extend(res)

    out_df = pd.DataFrame(all_res)
    out_df.to_csv(OUT_SUMMARY, index=False)
    print("\n" + "=" * 90)
    print("混杂感知分层评估结果 (Stratified LOGO Benchmark Summary):")
    print("=" * 90)
    print(out_df.to_string(index=False))
    print(f"\n已成功保存至 {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
