# -*- coding: utf-8 -*-
"""15_train_hierarchical_bb_nob879.py — 生产级正式训练脚本：noB879 纯A级金标准人群 + 形态二 (分层选择性 Beta-Binomial GLMM)

依据 2026-09-21 团队模型决策：
1. 训练集口径：noB879（剔除 90 行未确认候选的 B 级脏数据，纯 879 行 A 级金标准）；
2. 模型架构：形态二（Hierarchical Selective Beta-Binomial GLMM）；
   - 似然层：k_i ~ BetaBinomial(n_i, p_i, s), logit(p_i) = beta_0 + Z_i^T beta + u_{b_i}
   - 先验层：Selective EB Prior，充分锚点批次（>=10）紧约束，稀疏批次 EB 收缩，零批次先验归零；
   - 序列推断：剔除批次随机截距 u_b，仅输出纯序列生物学活性 eta = beta_0 + Z^T beta；
3. 输出模型产物：results/meta_model_hier_bb_nob879_0921.joblib
4. 运行：python scripts/15_train_hierarchical_bb_nob879.py
"""

import os
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut
import torch
import torch.nn as nn
import torch.optim as optim

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
XLSX_PATH = BASE_DIR / "data" / "1_Hi-results-16.1-efficiency-20260921.xlsx"
READS_CSV = BASE_DIR / "data" / "hitom" / "hitom_reads_depth_0921.csv"
MODEL_OUT = BASE_DIR / "results" / "meta_model_hier_bb_nob879_0921.joblib"
METRICS_CSV = BASE_DIR / "results" / "metrics_hier_bb_nob879_0921.csv"
FOLDS_CSV = BASE_DIR / "results" / "folds_hier_bb_nob879_0921.csv"

# 1. 载入并筛选人群
a = pd.read_excel(XLSX_PATH, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])
print(f"载入 noB879 纯A级金标准人群: n={len(pop_noB)} (已剔除 90 行未经设计表确认的 B 级数据)")
assert len(pop_noB) == 879, f"期望 879 行，实际 {len(pop_noB)} 行"

# 2. 基础特征与深度匹配
base = pd.read_csv(BASE_DIR / "data" / "hitom" / "hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv(BASE_DIR / "results" / "scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv(BASE_DIR / "results" / "scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
reads_df = pd.read_csv(READS_CSV)
base = base.merge(reads_df[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

df = base[base.guide_id.isin(pop_noB)].copy().reset_index(drop=True)
assert len(df) == 879

# 3. 特征工程
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

X_raw = df[FEATURE_COLS].astype(float).values
groups = df["gene_group"].values
indel = df["indel_pct"].astype(float)
n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

# 4. 批次先验与经验贝叶斯估计
p0 = np.clip(indel.median(), 0.05, 0.95)
logit_p0 = float(np.log(p0 / (1.0 - p0)))

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
        u_prec[i] = 10.0
    elif m > 0:
        u_prec[i] = 1.0 + float(m)
    else:
        u_prec[i] = 1.0

# 5. 模型优化器定义
def lbeta_torch(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)

def fit_hierarchical_selective_bb(X_tr, n_tr, k_tr, b_tr, n_b, u_p, u_prc, lp0,
                                 l2_beta=0.01, prior_scale=5.0, max_iter=200):
    mu = X_tr.mean(axis=0)
    std = X_tr.std(axis=0) + 1e-6
    Z_tr = (X_tr - mu) / std
    D = Z_tr.shape[1]

    X_t = torch.tensor(Z_tr, dtype=torch.float32)
    n_t = torch.tensor(n_tr, dtype=torch.float32)
    k_t = torch.tensor(k_tr, dtype=torch.float32)
    b_t = torch.tensor(b_tr, dtype=torch.long)
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

        prior_penalty = 0.5 * torch.sum(u_prec_t * (u - u_prior_t)**2)
        loss = -torch.mean(ll) + 0.5 * l2_beta * torch.sum(beta**2) + (prior_penalty / len(n_t))
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(beta0.detach().numpy()[0]), beta.detach().numpy(), mu, std, float(torch.exp(log_s).detach().numpy()[0])

# 6. 严密交叉验证与独立测试集评估
print("\n--- 正在执行独立测试集与 LOGO-CV 验证 ---")
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr_idx, te_idx = next(gss.split(X_raw, indel, groups))
b0_tr, w_tr, mu_tr, std_tr, s_tr = fit_hierarchical_selective_bb(
    X_raw[tr_idx], n_reads[tr_idx], k_reads[tr_idx], batch_idx[tr_idx],
    n_batches, u_prior, u_prec, logit_p0, prior_scale=5.0
)
Z_te = (X_raw[te_idx] - mu_tr) / std_tr
test_preds = b0_tr + np.dot(Z_te, w_tr)
test_rho, test_p = spearmanr(test_preds, indel.values[te_idx])
print(f"独立测试集 (20% 留出): Spearman rho = {test_rho:+.4f} (p = {test_p:.4e})")

# LOGO 交叉验证
ct = pd.crosstab(df["batch"], df["gene_group"])
class_a_genes = set([g for g in ct.columns if len(ct[g][ct[g] > 0]) >= 3])

fold_results = []
for tr_i, te_i in LeaveOneGroupOut().split(X_raw, indel, groups):
    grp = groups[te_i][0]
    b0_i, w_i, mu_i, std_i, _ = fit_hierarchical_selective_bb(
        X_raw[tr_i], n_reads[tr_i], k_reads[tr_i], batch_idx[tr_i],
        n_batches, u_prior, u_prec, logit_p0, prior_scale=5.0
    )
    Z_te_i = (X_raw[te_i] - mu_i) / std_i
    pred_i = b0_i + np.dot(Z_te_i, w_i)
    y_te = indel.values[te_i]
    is_class_a = grp in class_a_genes
    strat_class = "Class A (Low-Confounding, Multi-Batch)" if is_class_a else "Class B (High-Confounding, 1-2 Batches)"

    if len(set(np.round(y_te, 6))) > 1 and len(set(np.round(pred_i, 6))) > 1:
        r, p_val = spearmanr(pred_i, y_te)
        fold_results.append({
            "gene_group": grp,
            "class": strat_class,
            "n_samples": len(te_i),
            "rho": round(r, 4),
            "p_value": round(p_val, 4)
        })

folds_df = pd.DataFrame(fold_results)
folds_df.to_csv(FOLDS_CSV, index=False)

all_med_rho = float(folds_df["rho"].median())
class_a_med_rho = float(folds_df[folds_df["class"].str.startswith("Class A")]["rho"].median())
class_b_med_rho = float(folds_df[folds_df["class"].str.startswith("Class B")]["rho"].median())

print(f"LOGO-CV 全折中位相关系数: {all_med_rho:+.4f} (有效折: {len(folds_df)}/{len(set(groups))})")
print(f"Class A (低混杂多批折) 中位相关系数 (真实生物学上限): {class_a_med_rho:+.4f}")
print(f"Class B (高混杂孤岛折) 中位相关系数: {class_b_med_rho:+.4f}")

# 7. 全量数据拟合落盘模型
print("\n--- 正在拟合全量 noB879 生产模型权重 ---")
final_b0, final_w, final_mu, final_std, final_s = fit_hierarchical_selective_bb(
    X_raw, n_reads, k_reads, batch_idx, n_batches, u_prior, u_prec, logit_p0,
    prior_scale=5.0, max_iter=300
)

model_payload = {
    "model_name": "Hierarchical_Selective_BetaBinomial_GLMM_noB879",
    "version": "v2.1",
    "training_cohort": "noB879",
    "n_samples": len(df),
    "feature_cols": FEATURE_COLS,
    "beta0": final_b0,
    "beta": final_w,
    "mu": final_mu,
    "std": final_std,
    "dispersion_s": final_s,
    "test_rho": round(test_rho, 4),
    "logo_cv_median_rho": round(all_med_rho, 4),
    "class_a_median_rho": round(class_a_med_rho, 4),
    "class_b_median_rho": round(class_b_med_rho, 4),
    "prior_scale": 5.0,
    "l2_beta": 0.01,
}

joblib.dump(model_payload, MODEL_OUT)
print(f"生产模型已成功落盘至: {MODEL_OUT}")

# 8. 保存指标摘要
metrics_summary = pd.DataFrame([{
    "model": "Hierarchical_Selective_BB",
    "cohort": "noB879",
    "n_samples": 879,
    "test_rho": round(test_rho, 4),
    "logo_cv_median_rho": round(all_med_rho, 4),
    "class_a_median_rho": round(class_a_med_rho, 4),
    "class_b_median_rho": round(class_b_med_rho, 4),
    "valid_folds": f"{len(folds_df)}/{len(set(groups))}"
}])
metrics_summary.to_csv(METRICS_CSV, index=False)
print("\n指标摘要:")
print(metrics_summary.to_string(index=False))
