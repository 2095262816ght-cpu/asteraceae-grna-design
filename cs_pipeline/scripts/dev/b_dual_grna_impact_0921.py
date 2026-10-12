# -*- coding: utf-8 -*-
"""b_dual_grna_impact_0921.py — 评估 noB879 中 38 行双 gRNA 块对形态二模型的影响（遗留事项 P1）

对比三档方案：
1. baseline_noB879 (879行): 当前生产基准
2. drop_dual_841 (841行): 完全剔除 38 行双 gRNA 块
3. downweight_dual (879行): 双 gRNA 块在似然损失中按 0.5 降权

输出: results/b_dual_grna_impact_0921.csv
运行: python scripts/dev/b_dual_grna_impact_0921.py
"""

from pathlib import Path
import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut
import torch
import torch.nn as nn
import torch.optim as optim

BASE = Path(__file__).resolve().parent.parent.parent
XLSX = BASE / "data" / "1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = BASE / "data" / "hitom" / "hitom_reads_depth_0921.csv"
OUT_CSV = BASE / "results" / "b_dual_grna_impact_0921.csv"

# 1. 人群提取与标记
a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])

base = pd.read_csv(BASE / "data" / "hitom" / "hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv(BASE / "results" / "scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv(BASE / "results" / "scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
reads_df = pd.read_csv(READS_CSV)
base = base.merge(reads_df[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

df = base[base.guide_id.isin(pop_noB)].copy().reset_index(drop=True)
assert len(df) == 879

# 提取双gRNA标记
dual_gids = set(a[a["判定依据"].astype(str).str.contains("双gRNA")]["guide-id"].astype(str))
df["is_dual"] = df["guide_id"].isin(dual_gids)
print(f"noB879 中双 gRNA 行数: {df['is_dual'].sum()} (非双 gRNA: {(~df['is_dual']).sum()})")

HOMOLOG = {
    "EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
    "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"
}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)
df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)

FEATURE_COLS = [
    "deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
    "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_G", "pam_n_T"
]
for col in FEATURE_COLS:
    if col not in df.columns:
        df[col] = 0.0

ct = pd.crosstab(df["batch"], df["gene_group"])
class_a_genes = set([g for g in ct.columns if len(ct[g][ct[g] > 0]) >= 3])

def lbeta_torch(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)

def fit_hierarchical_selective_bb_weighted(X_tr, n_tr, k_tr, b_tr, w_sample, n_b, u_p, u_prc, lp0,
                                           l2_beta=0.01, prior_scale=5.0, max_iter=200):
    mu = X_tr.mean(axis=0)
    std = X_tr.std(axis=0) + 1e-6
    Z_tr = (X_tr - mu) / std
    D = Z_tr.shape[1]

    X_t = torch.tensor(Z_tr, dtype=torch.float32)
    n_t = torch.tensor(n_tr, dtype=torch.float32)
    k_t = torch.tensor(k_tr, dtype=torch.float32)
    b_t = torch.tensor(b_tr, dtype=torch.long)
    w_t = torch.tensor(w_sample, dtype=torch.float32)
    u_prior_t = torch.tensor(u_p, dtype=torch.float32)
    u_prec_t = torch.tensor(u_prc * prior_scale, dtype=torch.float32)

    beta0 = nn.Parameter(torch.tensor([lp0], dtype=torch.float32))
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

        log_comb = torch.lgamma(n_t + 1) - torch.lgamma(k_t + 1) - torch.lgamma(n_t - k_t + 1)
        ll = log_comb + lbeta_torch(k_t + alpha, n_t - k_t + beta_p) - lbeta_torch(alpha, beta_p)

        # 样本权重 w_t 调节每个样本在负对数似然中的贡献
        prior_penalty = 0.5 * torch.sum(u_prec_t * (u - u_prior_t)**2)
        weighted_nll = -torch.sum(w_t * ll) / torch.sum(w_t)
        loss = weighted_nll + 0.5 * l2_beta * torch.sum(beta**2) + (prior_penalty / len(n_t))
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(beta0.detach().numpy()[0]), beta.detach().numpy(), mu, std

def eval_experiment(df_exp, sample_weights, exp_name):
    X_raw = df_exp[FEATURE_COLS].astype(float).values
    groups = df_exp["gene_group"].values
    indel = df_exp["indel_pct"].astype(float)
    n_reads = np.maximum(df_exp["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

    p0 = np.clip(indel.median(), 0.05, 0.95)
    logit_p0 = float(np.log(p0 / (1.0 - p0)))

    shared = df_exp.groupby("seq20")["batch"].nunique()
    shared = set(shared[shared >= 2].index)
    gmed = df_exp[df_exp.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()

    offsets = {}
    anchor_counts = {}
    diff_residuals = []
    for b, sub in df_exp.groupby("batch"):
        s = sub[sub.seq20.isin(shared)]
        anchor_counts[b] = len(s)
        if len(s):
            diff = s["indel_pct"] - s.seq20.map(gmed)
            offsets[b] = float(diff.median())
            if len(s) > 1:
                diff_residuals.extend(diff - diff.mean())
        else:
            offsets[b] = 0.0

    s2 = float(np.var(diff_residuals)) if diff_residuals else 0.04
    offs_valid = [offsets[b] for b in offsets if anchor_counts.get(b, 0) > 0]
    tau2 = float(max(1e-4, np.var(offs_valid) - s2 / np.mean([anchor_counts[b] for b in offsets if anchor_counts.get(b, 0) > 0])))
    lambda_eb = float(s2 / tau2)

    selective_offsets = {}
    for b in offsets:
        m = anchor_counts.get(b, 0)
        if m >= 10:
            selective_offsets[b] = offsets[b]
        elif m > 0:
            selective_offsets[b] = (m / (m + lambda_eb)) * offsets[b]
        else:
            selective_offsets[b] = 0.0

    batch_cats = pd.Categorical(df_exp["batch"])
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
            u_prec[i] = 10.0
        elif m > 0:
            u_prec[i] = 1.0 + float(m)
        else:
            u_prec[i] = 1.0

    # 独立测试集
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(X_raw, indel, groups))
    b0_tr, w_tr, mu_tr, std_tr = fit_hierarchical_selective_bb_weighted(
        X_raw[tr_idx], n_reads[tr_idx], k_reads[tr_idx], batch_idx[tr_idx],
        sample_weights[tr_idx], n_batches, u_prior, u_prec, logit_p0
    )
    Z_te = (X_raw[te_idx] - mu_tr) / std_tr
    test_preds = b0_tr + np.dot(Z_te, w_tr)
    test_rho, test_p = spearmanr(test_preds, indel.values[te_idx])

    # LOGO CV
    fold_rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X_raw, indel, groups):
        grp = groups[te_i][0]
        b0_i, w_i, mu_i, std_i = fit_hierarchical_selective_bb_weighted(
            X_raw[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i],
            sample_weights[tr_i], n_batches, u_prior, u_prec, logit_p0
        )
        Z_te_i = (X_raw[te_i] - mu_i) / std_i
        pred_i = b0_i + np.dot(Z_te_i, w_i)
        y_te = indel.values[te_i]
        is_class_a = grp in class_a_genes
        if len(set(np.round(y_te, 6))) > 1 and len(set(np.round(pred_i, 6))) > 1:
            r, _ = spearmanr(pred_i, y_te)
            fold_rhos.append({"grp": grp, "class_a": is_class_a, "rho": r})

    f_df = pd.DataFrame(fold_rhos)
    med_all = float(f_df["rho"].median())
    med_class_a = float(f_df[f_df["class_a"]]["rho"].median())

    print(f"[{exp_name:18s}] n={len(df_exp)} Test_rho={test_rho:+.4f} LOGO_med={med_all:+.4f} Class_A_med={med_class_a:+.4f} 有效折={len(f_df)}/{len(set(groups))}")
    return {
        "experiment": exp_name,
        "n_samples": len(df_exp),
        "test_rho": round(test_rho, 4),
        "logo_cv_median_rho": round(med_all, 4),
        "class_a_median_rho": round(med_class_a, 4),
        "valid_folds": f"{len(f_df)}/{len(set(groups))}"
    }

results = []

# 实验 1: 现行生产基线 (noB879, 全权 1.0)
w_full = np.ones(len(df))
results.append(eval_experiment(df, w_full, "1_baseline_noB879"))

# 实验 2: 完全剔除 38 行双 gRNA 块
df_nodual = df[~df["is_dual"]].copy().reset_index(drop=True)
w_nodual = np.ones(len(df_nodual))
results.append(eval_experiment(df_nodual, w_nodual, "2_drop_dual_841"))

# 实验 3: 双 gRNA 块按 0.5 软降权
w_down = np.where(df["is_dual"], 0.5, 1.0)
results.append(eval_experiment(df, w_down, "3_downweight_dual_0.5"))

out_df = pd.DataFrame(results)
out_df.to_csv(OUT_CSV, index=False)
print("\n" + "=" * 80)
print("双 gRNA 块处理策略量化对比表:")
print("=" * 80)
print(out_df.to_string(index=False))
print(f"\n结果已保存至 {OUT_CSV}")
