# -*- coding: utf-8 -*-
"""hier_bb_model.py — 形态二（分层选择性 Beta-Binomial GLMM）的批次先验与拟合实现。

**单一来源**：`scripts/15`（生产训练）与 `scripts/24`（noB879 同口径模型对比表）共用本模块，
确保对比表里的"形态二"与生产模型出自同一段代码、同一套超参与同一先验——否则横向对比无效
（对比的会是两个不同的模型）。此前 `scripts/15` 是平铺脚本、无法被 import，任何第二个消费者
都只能复制一份拟合代码，那正是本项目刚在特征构建上消除的重复模式。

模型定义（2026-09-21 全队会签定案）：
    似然层  k_i ~ BetaBinomial(n_i, p_i, s),  logit(p_i) = beta_0 + Z_i·beta + u_{b_i}
    先验层  Selective EB Prior：充分锚点批次（锚点数 >= 10）紧约束、稀疏批次 EB 收缩、
            零锚点批次先验归零
    推断    剔除批次随机截距 u_b，仅输出纯序列生物学活性 eta = beta_0 + Z·beta

抽取时以"生产模型产物逐值不变"为验收标准：`results/meta_model_hier_bb_nob879_0921.joblib`
的 beta0 / beta / mu / std / dispersion_s 与 metrics、folds 两个 CSV 全部字节级或逐值相同。
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim


def compute_batch_prior(df):
    """由队列 df 计算选择性经验贝叶斯批次先验（原 scripts/15 第 4 节，逐行等价）。

    需要 df 含 `indel_pct`、`seq20`、`batch` 三列。
    返回 dict：logit_p0, u_prior, u_prec, batch_idx, n_batches, anchor_counts。
    """
    indel = df["indel_pct"].astype(float)
    p0 = np.clip(indel.median(), 0.05, 0.95)
    logit_p0 = float(np.log(p0 / (1.0 - p0)))

    # 跨批次共享的 seq20 才能当锚点：同一条 guide 出现在 >=2 个批次，
    # 其批次间 indel 差异即纯批次效应（序列效应被同一 guide 抵消）。
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
    tau2 = float(max(1e-4, np.var(offs_valid) - s2 / np.mean(
        [anchor_counts[b] for b in offsets if anchor_counts.get(b, 0) > 0])))
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

    return {
        "logit_p0": logit_p0,
        "u_prior": u_prior,
        "u_prec": u_prec,
        "batch_idx": batch_idx,
        "n_batches": n_batches,
        "anchor_counts": anchor_counts,
    }


def lbeta_torch(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)


def fit_hierarchical_selective_bb(X_tr, n_tr, k_tr, b_tr, n_b, u_p, u_prc, lp0,
                                  l2_beta=0.01, prior_scale=5.0, max_iter=200):
    """拟合形态二 GLMM（原 scripts/15 第 5 节，逐行等价）。

    X_tr 为原始（未标准化）特征矩阵；标准化用的 mu/std 在函数内由训练折自身算出并一并返回，
    以便对留出折做同一变换——这是避免测试集泄漏进标准化统计量的关键。
    返回 (beta0, beta, mu, std, dispersion_s)。
    """
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

    optimizer = optim.LBFGS([beta0, beta, u, log_s], lr=0.5, max_iter=max_iter,
                            line_search_fn="strong_wolfe")

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
    return (float(beta0.detach().numpy()[0]), beta.detach().numpy(), mu, std,
            float(torch.exp(log_s).detach().numpy()[0]))
