# -*- coding: utf-8 -*-
"""b_batch_effect_comparison_0921.py — 批次效应系统对比：Raw / Anchor / EB收缩 / 批内秩 / 深度加权 / Beta-二项GLMM

包含 6 种方法对比：
  1. raw: 原始 indel% 未校正 (Ridge)
  2. anchor: 当前中位数锚定偏移校正 (Ridge)
  3. eb_anchor: 经验贝叶斯(EB)收缩偏移量 (ComBat 思想, Ridge)
  4. rank: 批内百分位秩标签 (Method C, Ridge)
  5. depth_weighted_anchor: 测序深度加权 Anchor (Method A2 / WLS)
  6. betabinomial_glmm: 块级 reads 深度 Beta-二项 GLMM (Method A1, PyTorch)

人群 (16.1 口径):
  ruling1005 = 9.19裁决保留 ∩ 可打分 (1005行)
  train969   = 16.1 训练集 (969行)
  noB879     = train969 − B级90行 (879行)

输出: results/b_batch_effect_comparison_0921.csv
运行: python scripts/dev/b_batch_effect_comparison_0921.py
"""
import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = "data/hitom/hitom_reads_depth_0921.csv"
OUT_CSV = "results/b_batch_effect_comparison_0921.csv"

# 1. 人群提取
a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_ruling = set(gid_all[a["9.19裁决"] == "保留"])
pop_train = set(gid_all[a["处理状态"] == "保留"])
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])
print("人群(表级): ruling=%d train=%d noB=%d" % (len(pop_ruling), len(pop_train), len(pop_noB)))
assert len(pop_train) == 969 and len(pop_noB) == 879

# 2. 基础特征载入
base = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv("results/scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv("results/scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

# 载入深度
reads_df = pd.read_csv(READS_CSV)
base = base.merge(reads_df[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", how="left")
assert base["total_reads"].notna().all(), "深度信息存在缺失!"

HOMOLOG = {
    "EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
    "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"
}


def build_data(df):
    df = df.copy().reset_index(drop=True)
    df["note"] = df["note"].fillna("")
    df["gc_total"] = df.seq20.map(gc_fraction)
    df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
    df["tm"] = df.seq20.map(Tm_NN)
    df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
    df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
    df["gene_group"] = df["gene_id"].replace(HOMOLOG)

    # 1. 原始 indel
    indel = df["indel_pct"].astype(float)
    y_raw = (indel * 100.0).values

    # 2. 中位数锚定 Anchor
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

    y_anchor = ((indel - df["batch"].map(offsets).fillna(0.0)).clip(0, 1) * 100.0).values

    # 3. 经验贝叶斯 EB 收缩偏移量
    # 组内残差方差 s^2 与组间方差 tau^2
    s2 = np.var(diff_residuals) if diff_residuals else 0.04
    offs_valid = [offsets[b] for b in offsets if anchor_counts.get(b, 0) > 0]
    tau2 = max(1e-4, np.var(offs_valid) - s2 / np.mean([anchor_counts[b] for b in offsets if anchor_counts.get(b, 0) > 0]))
    lambda_eb = s2 / tau2

    eb_offsets = {}
    for b, off in offsets.items():
        m = anchor_counts.get(b, 0)
        eb_offsets[b] = (m / (m + lambda_eb)) * off

    y_eb = ((indel - df["batch"].map(eb_offsets).fillna(0.0)).clip(0, 1) * 100.0).values

    # 4. 批内百分位秩 (Method C)
    y_rank = (df.groupby("batch")["indel_pct"].rank(pct=True) * 100.0).values

    # 5. 测序深度与编辑数
    n_reads = df["total_reads"].values.astype(float)
    # 为避免个别极低 reads，设置底限 10 reads
    n_reads = np.maximum(n_reads, 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

    # 权重 (深度归一化)
    depth_weights = n_reads / np.mean(n_reads)

    return df, y_raw, y_anchor, y_eb, y_rank, n_reads, k_reads, depth_weights, offsets, eb_offsets


def feats(df):
    return [c for c in df.columns
            if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]


def eval_ridge_label(X, y_train, y_eval, groups, name, pop, n, sample_weights=None):
    """评估基于 Ridge 的方法 (raw, anchor, eb, rank, depth_weighted)"""
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y_train, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y_train[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv,
                      scoring="neg_mean_squared_error")
    sw_tr = sample_weights[tr] if sample_weights is not None else None
    gs.fit(X[tr], y_train[tr], sample_weight=sw_tr)
    rho = spearmanr(gs.best_estimator_.predict(X[te]), y_eval[te])[0]

    rhos = []
    fold_details = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y_train, groups):
        grp_name = groups[te_i][0]
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y_train[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i,
                           scoring="neg_mean_squared_error")
        sw_tr_i = sample_weights[tr_i] if sample_weights is not None else None
        g_i.fit(X[tr_i], y_train[tr_i], sample_weight=sw_tr_i)
        p_i = g_i.best_estimator_.predict(X[te_i])

        # round(6) 双侧常数折守卫
        if len(set(np.round(y_eval[te_i], 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
            r = spearmanr(p_i, y_eval[te_i])[0]
            rhos.append(r)
            fold_details.append((grp_name, len(te_i), r))

    med = float(np.nanmedian(rhos))
    print(f"[{pop:11s}|{name:21s}] n={n} test_rho={rho:+.4f} LOGO中位rho={med:+.4f} 有效折={len(rhos)}/{len(set(groups))}")
    return {
        "population": pop,
        "method": name,
        "n_rows": n,
        "test_rho": round(rho, 4),
        "logo_cv_median_rho": round(med, 4),
        "n_folds": len(rhos),
        "n_groups": len(set(groups)),
        "fold_details": fold_details
    }


def lbeta_torch(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)


def fit_betabinomial_glmm(X_tr, n_tr, k_tr, b_tr, n_batches, l2_beta=0.01, l2_u=1.0, max_iter=150):
    """训练 Beta-Binomial GLMM (PyTorch L-BFGS)"""
    mu = X_tr.mean(axis=0)
    std = X_tr.std(axis=0) + 1e-6
    Z_tr = (X_tr - mu) / std
    D = Z_tr.shape[1]

    X_t = torch.tensor(Z_tr, dtype=torch.float32)
    n_t = torch.tensor(n_tr, dtype=torch.float32)
    k_t = torch.tensor(k_tr, dtype=torch.float32)
    b_t = torch.tensor(b_tr, dtype=torch.long)

    beta0 = nn.Parameter(torch.zeros(1))
    beta = nn.Parameter(torch.zeros(D))
    u = nn.Parameter(torch.zeros(n_batches))
    log_s = nn.Parameter(torch.tensor([3.0]))  # s = precision

    optimizer = optim.LBFGS([beta0, beta, u, log_s], lr=0.5, max_iter=max_iter, line_search_fn="strong_wolfe")

    def closure():
        optimizer.zero_grad()
        s = torch.exp(log_s).clamp(1.0, 500.0)
        eta = beta0 + torch.matmul(X_t, beta) + u[b_t]
        p = torch.sigmoid(eta).clamp(1e-5, 1.0 - 1e-5)
        alpha = p * s
        beta_p = (1.0 - p) * s
        log_comb = torch.lgamma(n_t + 1) - torch.lgamma(k_t + 1) - torch.lgamma(n_t - k_t + 1)
        ll = log_comb + lbeta_torch(k_t + alpha, n_t - k_t + beta_p) - lbeta_torch(alpha, beta_p)
        loss = -torch.mean(ll) + 0.5 * l2_beta * torch.sum(beta**2) + 0.5 * l2_u * torch.sum(u**2)
        loss.backward()
        return loss

    optimizer.step(closure)
    return beta0.detach().numpy(), beta.detach().numpy(), mu, std


def eval_betabinomial(X, n_reads, k_reads, batch_idx, n_batches, y_eval, groups, name, pop, n):
    """评估 Beta-Binomial GLMM 模型 (测试集评价纯序列效应 eta = X w)"""
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y_eval, groups))

    b0, w, mu, std = fit_betabinomial_glmm(X[tr], n_reads[tr], k_reads[tr], batch_idx[tr], n_batches)
    Z_te = (X[te] - mu) / std
    pred_te = b0 + np.dot(Z_te, w)
    rho = spearmanr(pred_te, y_eval[te])[0]

    rhos = []
    fold_details = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y_eval, groups):
        grp_name = groups[te_i][0]
        b0_i, w_i, mu_i, std_i = fit_betabinomial_glmm(X[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i], n_batches)
        Z_te_i = (X[te_i] - mu_i) / std_i
        pred_i = b0_i + np.dot(Z_te_i, w_i)

        if len(set(np.round(y_eval[te_i], 6))) > 1 and len(set(np.round(pred_i, 6))) > 1:
            r = spearmanr(pred_i, y_eval[te_i])[0]
            rhos.append(r)
            fold_details.append((grp_name, len(te_i), r))

    med = float(np.nanmedian(rhos))
    print(f"[{pop:11s}|{name:21s}] n={n} test_rho={rho:+.4f} LOGO中位rho={med:+.4f} 有效折={len(rhos)}/{len(set(groups))}")
    return {
        "population": pop,
        "method": name,
        "n_rows": n,
        "test_rho": round(rho, 4),
        "logo_cv_median_rho": round(med, 4),
        "n_folds": len(rhos),
        "n_groups": len(set(groups)),
        "fold_details": fold_details
    }


def main():
    res = []
    fold_records = []

    populations = [
        ("train969", pop_train),
        ("noB879", pop_noB),
        ("ruling1005", pop_ruling)
    ]

    for pop, gids in populations:
        df = base[base.guide_id.isin(gids)].copy()
        df, y_raw, y_anchor, y_eb, y_rank, n_reads, k_reads, depth_weights, offsets, eb_offsets = build_data(df)

        X = df[feats(df)].astype(float).values
        groups = df["gene_group"].values
        batch_cats = pd.Categorical(df["batch"])
        batch_idx = batch_cats.codes
        n_batches = len(batch_cats.categories)

        print(f"\n==================== {pop}: n={len(df)} 基因组={len(set(groups))} 批次={n_batches} ====================")

        # 1. Baseline: Raw
        r1 = eval_ridge_label(X, y_raw, y_raw, groups, "raw", pop, len(df))
        res.append(r1)

        # 2. Baseline: Anchor (Median offset)
        r2 = eval_ridge_label(X, y_anchor, y_anchor, groups, "anchor", pop, len(df))
        res.append(r2)

        # 3. Method B: Empirical Bayes Shrinkage (EB Anchor)
        r3 = eval_ridge_label(X, y_eb, y_anchor, groups, "eb_anchor", pop, len(df))
        res.append(r3)

        # 4. Method C: Within-batch Percentile Rank (vs Rank target)
        r4 = eval_ridge_label(X, y_rank, y_rank, groups, "rank_vs_rank", pop, len(df))
        res.append(r4)

        # 4b. Method C: Within-batch Percentile Rank (vs Anchor benchmark)
        r4b = eval_ridge_label(X, y_rank, y_anchor, groups, "rank_vs_anchor", pop, len(df))
        res.append(r4b)

        # 5. Method A2: Depth-Weighted Anchor (WLS GLM approximation)
        r5 = eval_ridge_label(X, y_anchor, y_anchor, groups, "depth_weighted_anchor", pop, len(df), sample_weights=depth_weights)
        res.append(r5)

        # 6. Method A1: Beta-Binomial GLMM (vs Anchor benchmark)
        r6 = eval_betabinomial(X, n_reads, k_reads, batch_idx, n_batches, y_anchor, groups, "betabinomial_glmm", pop, len(df))
        res.append(r6)

        # 6b. Method A1: Beta-Binomial GLMM (vs Raw target)
        r6b = eval_betabinomial(X, n_reads, k_reads, batch_idx, n_batches, y_raw, groups, "betabinomial_vs_raw", pop, len(df))
        res.append(r6b)

        # 收集折级明细
        for r_dict in [r1, r2, r3, r4, r4b, r5, r6, r6b]:
            for grp, f_n, f_rho in r_dict["fold_details"]:
                fold_records.append({
                    "population": pop,
                    "method": r_dict["method"],
                    "gene_group": grp,
                    "n_guides": f_n,
                    "rho": round(f_rho, 4)
                })

    out = pd.DataFrame([{k: v for k, v in r.items() if k != "fold_details"} for r in res])
    out.to_csv(OUT_CSV, index=False)
    print("\n" + "=" * 80)
    print("全量对比结果 (Results Summary):")
    print("=" * 80)
    print(out.to_string())
    print(f"\nSaved summary to {OUT_CSV}")

    # 保存折级明细供深度诊断
    fold_df = pd.DataFrame(fold_records)
    fold_csv = "results/b_batch_effect_fold_details_0921.csv"
    fold_df.to_csv(fold_csv, index=False)
    print(f"Saved fold details to {fold_csv}")


if __name__ == "__main__":
    main()
