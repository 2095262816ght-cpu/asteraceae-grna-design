# -*- coding: utf-8 -*-
"""b_hierarchical_selective_bb_0921.py — 形态二：分段经验贝叶斯先验的 Beta-二项分层模型 (A1 + A2 + Selective B)

核心架构：
  1. 似然层 (A1 + A2)：
     k_i ~ BetaBinomial(n_i, p_i, s), logit(p_i) = beta_0 + x_i^T beta + u_{b_i}
     总测序 reads 深度 n_i 直接作为试验次数，自适应控制测量精度与异方差。
  2. 先验层 (Selective B)：
     针对暗坑（USR-6137 材料基线偏移高达 +87%，若统一收缩会留下残差被大深度放大）：
     - 充分锚点批次 (m_b >= 10)：完全采信锚点物理偏移，赋予强先验精度约束 (weight=10.0)，防止截距被无信息平滑或吞噬生物学信号；
     - 稀疏锚点批次 (0 < m_b < 10)：实施经验贝叶斯收缩 Delta_b^EB = m / (m + lambda) * Delta_b，中度先验约束；
     - 0 锚点批次 (m_b == 0)：收缩归零，标准高斯正则化。
  3. 序列预测：
     测试集评估纯序列效应 eta = x_test^T beta，不受批次偏移干扰。

输出: results/b_hierarchical_selective_bb_0921.csv
运行: D:\Miniconda\envs\crispr\python.exe scripts/dev/b_hierarchical_selective_bb_0921.py
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
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = "data/hitom/hitom_reads_depth_0921.csv"
OUT_CSV = "results/b_hierarchical_selective_bb_0921.csv"

# 1. 载入人群
a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_ruling = set(gid_all[a["9.19裁决"] == "保留"])
pop_train = set(gid_all[a["处理状态"] == "保留"])
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])

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


def build_cohort_data(df):
    df = df.copy().reset_index(drop=True)
    df["note"] = df["note"].fillna("")
    df["gc_total"] = df.seq20.map(gc_fraction)
    df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
    df["tm"] = df.seq20.map(Tm_NN)
    df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
    df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
    df["gene_group"] = df["gene_id"].replace(HOMOLOG)

    indel = df["indel_pct"].astype(float)
    y_raw = (indel * 100.0).values
    p0 = np.clip(indel.median(), 0.05, 0.95)
    logit_p0 = np.log(p0 / (1.0 - p0))

    # 锚点与方差估计
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
    lambda_eb = s2 / tau2

    # 分段经验贝叶斯 (Selective EB) 策略
    selective_offsets = {}
    for b in offsets:
        m = anchor_counts.get(b, 0)
        if m >= 10:
            # 充分锚点（含 USR-6137）：完全采信，不因全局收缩产生残差
            selective_offsets[b] = offsets[b]
        elif m > 0:
            # 稀疏锚点（如 USR-23709）：EB 收缩防噪声
            selective_offsets[b] = (m / (m + lambda_eb)) * offsets[b]
        else:
            selective_offsets[b] = 0.0

    y_anchor = ((indel - df["batch"].map(offsets).fillna(0.0)).clip(0, 1) * 100.0).values

    batch_cats = pd.Categorical(df["batch"])
    batch_idx = batch_cats.codes
    n_batches = len(batch_cats.categories)

    u_prior = np.zeros(n_batches)
    u_prec = np.zeros(n_batches)

    for i, b_name in enumerate(batch_cats.categories):
        delta = selective_offsets.get(b_name, 0.0)
        p_b = np.clip(p0 + delta, 0.005, 0.995)
        u_prior[i] = np.log(p_b / (1.0 - p_b)) - logit_p0
        m = anchor_counts.get(b_name, 0)
        if m >= 10:
            u_prec[i] = 10.0  # 紧约束锚定
        elif m > 0:
            u_prec[i] = 1.0 + float(m)  # 按信息量适度约束
        else:
            u_prec[i] = 1.0  # 零均值正则化

    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

    return df, y_raw, y_anchor, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, p0, logit_p0


def feats(df):
    return [c for c in df.columns
            if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]


def lbeta_torch(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)


def fit_hierarchical_selective_bb(X_tr, n_tr, k_tr, b_tr, n_batches, u_prior, u_prec, logit_p0,
                                 l2_beta=0.01, prior_scale=1.0, max_iter=150):
    """拟合带分段 EB 先验的 Beta-Binomial GLMM"""
    mu = X_tr.mean(axis=0)
    std = X_tr.std(axis=0) + 1e-6
    Z_tr = (X_tr - mu) / std
    D = Z_tr.shape[1]

    X_t = torch.tensor(Z_tr, dtype=torch.float32)
    n_t = torch.tensor(n_tr, dtype=torch.float32)
    k_t = torch.tensor(k_tr, dtype=torch.float32)
    b_t = torch.tensor(b_tr, dtype=torch.long)
    u_prior_t = torch.tensor(u_prior, dtype=torch.float32)
    u_prec_t = torch.tensor(u_prec * prior_scale, dtype=torch.float32)

    beta0 = nn.Parameter(torch.tensor([logit_p0], dtype=torch.float32))
    beta = nn.Parameter(torch.zeros(D))
    u = nn.Parameter(u_prior_t.clone())
    log_s = nn.Parameter(torch.tensor([3.0]))

    optimizer = optim.LBFGS([beta0, beta, u, log_s], lr=0.5, max_iter=max_iter, line_search_fn="strong_wolfe")

    def closure():
        optimizer.zero_grad()
        s = torch.exp(log_s).clamp(1.0, 500.0)
        eta = beta0 + torch.matmul(X_t, beta) + u[b_t]
        p = torch.sigmoid(eta).clamp(1e-5, 1.0 - 1e-5)
        alpha = p * s
        beta_p = (1.0 - p) * s

        # Beta-Binomial 边缘对数似然
        log_comb = torch.lgamma(n_t + 1) - torch.lgamma(k_t + 1) - torch.lgamma(n_t - k_t + 1)
        ll = log_comb + lbeta_torch(k_t + alpha, n_t - k_t + beta_p) - lbeta_torch(alpha, beta_p)

        # 联合目标: NLL + L2(beta) + Selective EB 先验惩罚
        prior_penalty = 0.5 * torch.sum(u_prec_t * (u - u_prior_t)**2)
        loss = -torch.mean(ll) + 0.5 * l2_beta * torch.sum(beta**2) + (prior_penalty / len(n_t))
        loss.backward()
        return loss

    optimizer.step(closure)
    return beta0.detach().numpy(), beta.detach().numpy(), mu, std


def eval_model(X, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, logit_p0, y_eval, groups,
               name, pop, n, prior_scale=1.0):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y_eval, groups))

    b0, w, mu, std = fit_hierarchical_selective_bb(
        X[tr], n_reads[tr], k_reads[tr], batch_idx[tr], n_batches,
        u_prior, u_prec, logit_p0, prior_scale=prior_scale
    )
    Z_te = (X[te] - mu) / std
    pred_te = b0 + np.dot(Z_te, w)
    rho = spearmanr(pred_te, y_eval[te])[0]

    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y_eval, groups):
        b0_i, w_i, mu_i, std_i = fit_hierarchical_selective_bb(
            X[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i], n_batches,
            u_prior, u_prec, logit_p0, prior_scale=prior_scale
        )
        Z_te_i = (X[te_i] - mu_i) / std_i
        pred_i = b0_i + np.dot(Z_te_i, w_i)
        y_te = y_eval[te_i]
        if len(set(np.round(y_te, 6))) > 1 and len(set(np.round(pred_i, 6))) > 1:
            rhos.append(spearmanr(pred_i, y_te)[0])

    med = float(np.nanmedian(rhos))
    print(f"[{pop:11s}|{name:28s}] n={n} test_rho={rho:+.4f} LOGO中位rho={med:+.4f} 有效折={len(rhos)}/{len(set(groups))}")
    return {
        "population": pop,
        "method": name,
        "n_rows": n,
        "test_rho": round(rho, 4),
        "logo_cv_median_rho": round(med, 4),
        "n_folds": len(rhos),
        "n_groups": len(set(groups))
    }


def main():
    res = []
    cohorts = [
        ("train969", pop_train),
        ("noB879", pop_noB),
        ("ruling1005", pop_ruling)
    ]

    for pop, gids in cohorts:
        df = base[base.guide_id.isin(gids)].copy()
        df, y_raw, y_anchor, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, p0, logit_p0 = build_cohort_data(df)
        X = df[feats(df)].astype(float).values
        groups = df["gene_group"].values

        print(f"\n==================== 评测形态二: {pop} (n={len(df)}) ====================")
        # 测试不同先验强度尺度 (prior_scale)
        for p_scale in [0.5, 1.0, 2.0, 5.0]:
            tag = f"hier_sel_bb_s{p_scale:.1f}"
            r = eval_model(
                X, n_reads, k_reads, batch_idx, n_batches,
                u_prior, u_prec, logit_p0, y_anchor, groups,
                tag, pop, len(df), prior_scale=p_scale
            )
            res.append(r)

    out = pd.DataFrame(res)
    out.to_csv(OUT_CSV, index=False)
    print("\n" + "=" * 80)
    print("形态二 (分段 EB 先验 Beta-Binomial) 全量评测结果:")
    print("=" * 80)
    print(out.to_string())
    print(f"\n已保存结果至 {OUT_CSV}")


if __name__ == "__main__":
    main()
