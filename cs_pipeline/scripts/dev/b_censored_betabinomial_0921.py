# -*- coding: utf-8 -*-
"""b_censored_betabinomial_0921.py — 针对饱和截断与双峰的删失 Beta-二项回归 (Censored Beta-Binomial)

针对根问题 2：
  - USR-5712 (42/61 饱和 >= 0.95, 中位数 1.0)
  - USR-6137 (38/67 饱和)
  - USR-5448 (15 个零值，双峰杂合)
核心逻辑：
  将极端值显式建模为删失状态（Censored State）：
  - indel >= 0.95: 视为右删失事件 P(k >= 0.95*n)，只要模型预测 p 落在饱和区就不产生无谓的边界拟合惩罚；
  - indel <= 0.01: 视为左删失事件 P(k <= 0.01*n)；
  - 0.01 < indel < 0.95: 正常的 Beta-二项连续似然。
输出: results/b_censored_bb_0921.csv
"""
import math
import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b_hierarchical_selective_bb_0921 import (
    build_cohort_data, feats, lbeta_torch
)
from b_identifiability_and_stratified_logo_0921 import analyze_confounding

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = "data/hitom/hitom_reads_depth_0921.csv"
OUT_CSV = "results/b_censored_bb_0921.csv"

a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_train = set(gid_all[a["处理状态"] == "保留"])
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])

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


def fit_censored_selective_bb(X_tr, n_tr, k_tr, b_tr, n_batches, u_prior, u_prec, logit_p0,
                              l2_beta=0.01, prior_scale=5.0, max_iter=150,
                              use_censoring=True, left_th=0.01, right_th=0.95):
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

    # 标记删失样本
    ratio = k_t / n_t
    is_right = (ratio >= right_th) if use_censoring else torch.zeros_like(ratio, dtype=torch.bool)
    is_left = (ratio <= left_th) if use_censoring else torch.zeros_like(ratio, dtype=torch.bool)
    is_mid = (~is_right) & (~is_left)

    k1 = right_th * n_t
    k0 = left_th * n_t

    def closure():
        optimizer.zero_grad()
        s = torch.exp(log_s).clamp(1.0, 500.0)
        eta = beta0 + torch.matmul(X_t, beta) + u[b_t]
        p = torch.sigmoid(eta).clamp(1e-5, 1.0 - 1e-5)
        alpha = p * s
        beta_p = (1.0 - p) * s

        ll = torch.zeros_like(n_t)

        # 连续区段
        if is_mid.any():
            km = k_t[is_mid]; nm = n_t[is_mid]; am = alpha[is_mid]; bm = beta_p[is_mid]
            log_comb = torch.lgamma(nm + 1) - torch.lgamma(km + 1) - torch.lgamma(nm - km + 1)
            ll[is_mid] = log_comb + lbeta_torch(km + am, nm - km + bm) - lbeta_torch(am, bm)

        # 右删失区段: P(k >= k1) 通过连续正态/CDF平滑近似
        if is_right.any():
            nr = n_t[is_right]; pr = p[is_right]; k1r = k1[is_right]
            mu_r = nr * pr
            var_r = nr * pr * (1.0 - pr) * ((s + nr) / (s + 1.0)) + 1e-4
            std_r = torch.sqrt(var_r)
            zr = (mu_r - k1r) / std_r
            # log survival: log(0.5 * erfc(-zr / sqrt(2)))
            ll[is_right] = torch.log(0.5 * torch.erfc(-zr / math.sqrt(2)) + 1e-12)

        # 左删失区段: P(k <= k0)
        if is_left.any():
            nl = n_t[is_left]; pl = p[is_left]; k0l = k0[is_left]
            mu_l = nl * pl
            var_l = nl * pl * (1.0 - pl) * ((s + nl) / (s + 1.0)) + 1e-4
            std_l = torch.sqrt(var_l)
            zl = (k0l - mu_l) / std_l
            ll[is_left] = torch.log(0.5 * torch.erfc(-zl / math.sqrt(2)) + 1e-12)

        prior_penalty = 0.5 * torch.sum(u_prec_t * (u - u_prior_t)**2)
        loss = -torch.mean(ll) + 0.5 * l2_beta * torch.sum(beta**2) + (prior_penalty / len(n_t))
        loss.backward()
        return loss

    optimizer.step(closure)
    return beta0.detach().numpy(), beta.detach().numpy(), mu, std


def run_eval(pop_name, gids, gene_class_map, use_censoring=True):
    df_sub = base[base.guide_id.isin(gids)].copy()
    df_sub, y_raw, y_anchor, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, p0, logit_p0 = build_cohort_data(df_sub)
    X = df_sub[feats(df_sub)].astype(float).values
    groups = df_sub["gene_group"].values

    tag = "Censored_BB" if use_censoring else "Standard_BB"
    print(f"\n--- {pop_name}: 评测 {tag} ---")

    # Test split
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y_anchor, groups))
    b0, w, mu, std = fit_censored_selective_bb(
        X[tr], n_reads[tr], k_reads[tr], batch_idx[tr], n_batches,
        u_prior, u_prec, logit_p0, use_censoring=use_censoring
    )
    pred_te = b0 + np.dot((X[te] - mu) / std, w)
    test_rho = spearmanr(pred_te, y_anchor[te])[0]

    # LOGO CV
    rhos_all = []
    rhos_a = []
    rhos_b = []

    for tr_i, te_i in LeaveOneGroupOut().split(X, y_anchor, groups):
        grp = groups[te_i][0]
        y_eval = y_anchor[te_i]
        grp_class = gene_class_map.get(grp, "Unknown")

        b0_i, w_i, mu_i, std_i = fit_censored_selective_bb(
            X[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i], n_batches,
            u_prior, u_prec, logit_p0, use_censoring=use_censoring
        )
        pred_i = b0_i + np.dot((X[te_i] - mu_i) / std_i, w_i)

        if len(set(np.round(y_eval, 6))) > 1 and len(set(np.round(pred_i, 6))) > 1:
            r = spearmanr(pred_i, y_eval)[0]
            rhos_all.append(r)
            if grp_class.startswith("Class A"):
                rhos_a.append(r)
            else:
                rhos_b.append(r)

    print(f"[{pop_name}|{tag}] Test_rho={test_rho:+.4f}, LOGO_med={np.nanmedian(rhos_all):+.4f}, Class_A={np.nanmedian(rhos_a):+.4f}, Class_B={np.nanmedian(rhos_b):+.4f}")
    return {
        "population": pop_name,
        "model": tag,
        "test_rho": round(test_rho, 4),
        "logo_med_rho": round(float(np.nanmedian(rhos_all)), 4),
        "class_a_med_rho (Low-Confounding)": round(float(np.nanmedian(rhos_a)), 4),
        "class_b_med_rho (High-Confounding)": round(float(np.nanmedian(rhos_b)), 4),
        "n_folds": len(rhos_all)
    }


def main():
    df_train = base[base.guide_id.isin(pop_train)].copy()
    df_train["gene_group"] = df_train["gene_id"].replace(HOMOLOG)
    gene_class_map = analyze_confounding(df_train)

    results = []
    for pop_name, gids in [("train969", pop_train), ("noB879", pop_noB)]:
        # 1. Standard (Uncensored)
        r_std = run_eval(pop_name, gids, gene_class_map, use_censoring=False)
        results.append(r_std)
        # 2. Censored
        r_cens = run_eval(pop_name, gids, gene_class_map, use_censoring=True)
        results.append(r_cens)

    out = pd.DataFrame(results)
    out.to_csv(OUT_CSV, index=False)
    print("\n" + "=" * 80)
    print("删失似然 (Censored BB) 评测结果:")
    print("=" * 80)
    print(out.to_string(index=False))
    print(f"已保存至 {OUT_CSV}")


if __name__ == "__main__":
    main()
