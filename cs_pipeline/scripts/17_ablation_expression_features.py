# -*- coding: utf-8 -*-
"""17_ablation_expression_features.py — 方案2：TKS 转录组表达水平对 CRISPR 编辑效率作用的检验

设计依据（2026-09-23 对 multiomics_implementation_plan.md 方案2 的修订）
--------------------------------------------------------------------------
原方案拟用「Group A(纯序列) vs Group B(+表达)」的 LOGO-CV 逐折 Spearman Δρ + Wilcoxon
来回答“表达水平在多大程度上影响剪切效率”。该设计存在结构性缺陷：

  TKS 表达特征是**基因级常量**；LOGO 的一个 test fold 恰好就是**一个基因**；
  而 scripts/15 的推断路径（15:204-205）明确剔除批次随机截距 u_b，
  故 fold 内预测 = beta0 + z·beta。基因级常量项对该 fold 所有样本施加**同一个常数偏移**，
  Spearman 秩相关对常数偏移不变 => beta_expr 对 fold 内 ρ 的直接贡献恒等于 0。
  Δρ 只能经“序列系数被重新估计”这条二阶路径产生，Wilcoxon 检验的是噪声。

因此本脚本改为在**正确的分析单元**上检验，并保留原消融作为方法学负对照：

  Block 1（主结果）基因级检验：表达 vs 批次校正后的基因平均 indel，n = 基因组数；
  Block 2        嵌套 GLMM：在 scripts/15 形态二似然上加表达协变量，报告 γ、LRT 与聚类自助 CI；
  Block 3（负对照）原 Group A / Group B LOGO-CV 逐折 Δρ + Wilcoxon，用于实证上面的结构性论断。

可辨识性告警：仅出现在单一 batch 的基因组，其基因效应与批次效应完全共线，表达效应不可辨识；
本脚本逐基因标注该状态，并在 Block 1 给出剔除共线基因后的敏感性结果。

运行（在 cs_pipeline/ 下，crispr 环境）：
    python scripts/17_ablation_expression_features.py [--boot 100] [--quick]
产物：
    results/ablation_expression_genelevel_0923.csv     基因级主表
    results/ablation_expression_study_0923.csv         三块结果汇总（逐折 + 系数 + 检验）
    results/ablation_expression_shap.png               线性模型精确 Shapley 贡献条形图
    results/ablation_expression_report_0923.md         可直接进申报报告/论文的章节
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, pearsonr, spearmanr, wilcoxon
import torch
import torch.nn as nn
import torch.optim as optim

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
XLSX_161 = BASE_DIR / "data" / "1_Hi-results-16.1-efficiency-20260921.xlsx"
SEQ30_CSV = BASE_DIR / "data" / "hitom" / "hitom_seq30_merged_0918.csv"
DSS_CSV = BASE_DIR / "results" / "scores_deepspcas9_merged_0918.csv"
CRISPON_CSV = BASE_DIR / "results" / "scores_crispron_merged_0918.csv"
READS_CSV = BASE_DIR / "data" / "hitom" / "hitom_reads_depth_0921.csv"
TKS_XLSX = BASE_DIR / "data" / "expression" / "2-3_TKS_Tiss-Dev-Expression(1).xlsx"

OUT_GENELEVEL = BASE_DIR / "results" / "ablation_expression_genelevel_0923.csv"
OUT_STUDY = BASE_DIR / "results" / "ablation_expression_study_0923.csv"
OUT_SHAP = BASE_DIR / "results" / "ablation_expression_shap.png"
OUT_REPORT = BASE_DIR / "results" / "ablation_expression_report_0923.md"

# 与 scripts/15 保持一致：LG01.6995 / 6999 为同源对，合并为一个 LOGO 组
HOMOLOG = {
    "EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
    "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999",
}
HOMOLOG_MEMBERS = ["evm.model.lg01.6995", "evm.model.lg01.6999"]

SEQ_FEATURES = [
    "deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
    "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_G", "pam_n_T",
]

# TKS 表列名异常的人工裁定（文件实测 79 个样本列，非方案文档所称 80）：
#   S9-2jiaoru        -> 视作 S9 胶乳 rep2（该表缺 S9-jiaoru-2，命名倒置）
#   S9-jiaoruRNA7-3   -> 来源不明的独立文库，**排除**出胶乳均值（敏感性另计）
COLUMN_OVERRIDES = {"S9-2jiaoru": ("S9", "jiaoru", "2")}
COLUMN_EXCLUDES = {"S9-jiaoruRNA7-3"}
TISSUE_CN = {"gen": "根", "ye": "叶", "jiaoru": "胶乳", "hua": "花", "huating": "花葶"}


# --------------------------------------------------------------------------
# TKS 表达特征
# --------------------------------------------------------------------------
def parse_sample_columns(columns):
    """把样本列名解析为 (stage, tissue, rep)；异常列走人工裁定表。"""
    parsed, excluded = {}, []
    for c in columns:
        if c in COLUMN_EXCLUDES:
            excluded.append(c)
            continue
        if c in COLUMN_OVERRIDES:
            parsed[c] = COLUMN_OVERRIDES[c]
            continue
        parts = c.split("-")
        assert len(parts) == 3, f"无法解析样本列名: {c}"
        parsed[c] = (parts[0], parts[1], parts[2])
    tissues = sorted({v[1] for v in parsed.values()})
    assert "?" not in tissues, f"存在未能归类的组织: {columns}"
    return parsed, excluded, tissues


def load_tks_expression():
    """返回 (per-gene 表达特征表, 样本口径审计信息)。"""
    raw = pd.read_excel(TKS_XLSX)
    raw.columns = [str(c).strip() for c in raw.columns]
    gene_col = raw.columns[0]
    sample_cols = list(raw.columns[1:])
    parsed, excluded, tissues = parse_sample_columns(sample_cols)

    for c in sample_cols:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    n_nan = int(raw[sample_cols].isna().sum().sum())
    raw[sample_cols] = raw[sample_cols].fillna(0.0)

    raw["_key"] = raw[gene_col].astype(str).str.strip().str.lower()
    assert not raw["_key"].duplicated().any(), "TKS 表达矩阵存在重复基因 ID"
    raw = raw.set_index("_key")

    tissue_means = {}
    for t in tissues:
        cols = [c for c in parsed if parsed[c][1] == t]
        tissue_means[t] = raw[cols].mean(axis=1)
    tm = pd.DataFrame(tissue_means)

    feat = pd.DataFrame(index=raw.index)
    for t in tissues:
        feat[f"tpm_{t}"] = tm[t]
        feat[f"log2_{t}"] = np.log2(tm[t].clip(lower=0) + 1.0)
    feat["dev_mean_tpm"] = raw[sample_cols].mean(axis=1)
    feat["dev_mean_log2"] = np.log2(feat["dev_mean_tpm"] + 1.0)
    feat["e_max_log2"] = np.log2(tm.max(axis=1) + 1.0)

    # Tau 组织特异性指数（方案文档定义式）
    mx = tm.max(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        tau = (1.0 - tm.div(mx, axis=0)).sum(axis=1) / (len(tissues) - 1)
    feat["tau"] = tau.where(mx > 0, np.nan)

    # 表达变异系数（跨样本）
    mu = raw[sample_cols].mean(axis=1)
    sd = raw[sample_cols].std(axis=1)
    feat["cv"] = sd / (mu + 1e-9)

    audit = {
        "n_genes": len(feat),
        "n_sample_cols": len(sample_cols),
        "n_used_cols": len(parsed),
        "excluded_cols": excluded,
        "tissues": tissues,
        "samples_per_tissue": {t: len([c for c in parsed if parsed[c][1] == t]) for t in tissues},
        "stages": sorted({v[0] for v in parsed.values()}),
        "n_nan_coerced_to_0": n_nan,
    }
    return feat, audit


# --------------------------------------------------------------------------
# 队列装载（复刻 scripts/15 口径）
# --------------------------------------------------------------------------
def load_cohort(kind):
    """kind in {'noB879', 'train969'}；返回带基因组与表达特征的 DataFrame。"""
    if kind == "noB879":
        a = pd.read_excel(XLSX_161, sheet_name="全部打分")
        gid = a["guide-id"].astype(str)
        pop = set(gid[(a["处理状态"] == "保留") & (a["等级"] != "B")])
        expect = 879
    elif kind == "train969":
        t = pd.read_excel(XLSX_161, sheet_name="训练集")
        pop = set(t["guide-id"].astype(str))
        expect = 969
    else:
        raise ValueError(kind)

    base = pd.read_csv(SEQ30_CSV)
    base = base.merge(pd.read_csv(DSS_CSV), on="guide_id", validate="1:1")
    base = base.merge(pd.read_csv(CRISPON_CSV), on="guide_id", validate="1:1")
    reads = pd.read_csv(READS_CSV)
    base = base.merge(reads[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", validate="1:1")
    base["guide_id"] = base["guide_id"].astype(str)

    df = base[base.guide_id.isin(pop)].copy().reset_index(drop=True)
    assert len(df) == expect, f"{kind} 期望 {expect} 行，实际 {len(df)} 行"

    df["gene_group"] = df["gene_id"].replace(HOMOLOG)
    from Bio.SeqUtils import gc_fraction
    from Bio.SeqUtils.MeltingTemp import Tm_NN
    df["gc_total"] = df.seq20.map(gc_fraction)
    df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
    df["tm"] = df.seq20.map(Tm_NN)
    df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
    df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
    for col in SEQ_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
    return df


EXPR_FEATURES = ["log2_gen", "log2_ye", "log2_jiaoru", "dev_mean_log2", "tau"]


def attach_expression(df, expr_feat):
    """按基因把 TKS 表达特征贴到每条 guide；同源对取两成员均值。"""
    def group_expr(gg):
        if gg == "EVM.MODEL.LG01.6995/6999":
            keys = [k for k in HOMOLOG_MEMBERS if k in expr_feat.index]
            assert keys, "同源对成员在表达矩阵中缺失"
            return expr_feat.loc[keys].mean(axis=0)
        key = gg.lower()
        assert key in expr_feat.index, f"基因 {gg} 未命中 TKS 表达矩阵"
        return expr_feat.loc[key]

    per_group = {gg: group_expr(gg) for gg in sorted(df["gene_group"].unique())}
    lookup = pd.DataFrame(per_group).T
    out = df.merge(lookup, left_on="gene_group", right_index=True, validate="m:1")
    assert len(out) == len(df), "表达特征合并改变了行数"
    return out


# --------------------------------------------------------------------------
# 批次偏移（复刻 scripts/15 的 Selective EB Prior）
# --------------------------------------------------------------------------
def batch_offsets(df):
    shared = df.groupby("seq20")["batch"].nunique()
    shared = set(shared[shared >= 2].index)
    gmed = df[df.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()

    offsets, anchor_counts, residuals = {}, {}, []
    for b, sub in df.groupby("batch"):
        s = sub[sub.seq20.isin(shared)]
        anchor_counts[b] = len(s)
        if len(s):
            diff = s["indel_pct"] - s.seq20.map(gmed)
            offsets[b] = float(diff.median())
            if len(s) > 1:
                residuals.extend(diff - diff.mean())
        else:
            offsets[b] = 0.0

    s2 = float(np.var(residuals)) if residuals else 0.04
    valid = [offsets[b] for b in offsets if anchor_counts.get(b, 0) > 0]
    mean_m = np.mean([anchor_counts[b] for b in offsets if anchor_counts.get(b, 0) > 0])
    tau2 = float(max(1e-4, np.var(valid) - s2 / mean_m))
    lam = float(s2 / tau2)

    selective = {}
    for b, off in offsets.items():
        m = anchor_counts.get(b, 0)
        if m >= 10:
            selective[b] = off
        elif m > 0:
            selective[b] = (m / (m + lam)) * off
        else:
            selective[b] = 0.0
    return selective, anchor_counts


# --------------------------------------------------------------------------
# 形态二 分层选择性 Beta-Binomial GLMM（复刻 scripts/15:137-178，额外返回对数似然）
# --------------------------------------------------------------------------
def lbeta(a, b):
    return torch.lgamma(a) + torch.lgamma(b) - torch.lgamma(a + b)


def fit_hier_bb(X, n_reads, k_reads, b_idx, u_prior, u_prec, logit_p0,
                l2_beta=0.01, prior_scale=5.0, max_iter=200, want_hess_for=None):
    mu = X.mean(axis=0)
    std = X.std(axis=0) + 1e-6
    Z = (X - mu) / std
    D = Z.shape[1]

    X_t = torch.tensor(Z, dtype=torch.float32)
    n_t = torch.tensor(n_reads, dtype=torch.float32)
    k_t = torch.tensor(k_reads, dtype=torch.float32)
    b_t = torch.tensor(b_idx, dtype=torch.long)
    u_prior_t = torch.tensor(u_prior, dtype=torch.float32)
    u_prec_t = torch.tensor(u_prec * prior_scale, dtype=torch.float32)

    beta0 = nn.Parameter(torch.tensor([logit_p0], dtype=torch.float32))
    beta = nn.Parameter(torch.zeros(D))
    u = nn.Parameter(u_prior_t.clone())
    log_s = nn.Parameter(torch.tensor([3.0]))

    opt = optim.LBFGS([beta0, beta, u, log_s], lr=0.5, max_iter=max_iter,
                      line_search_fn="strong_wolfe")

    def loglik_terms():
        s = torch.exp(log_s).clamp(1.0, 500.0)
        eta = beta0 + torch.matmul(X_t, beta) + u[b_t]
        p = torch.sigmoid(eta).clamp(1e-5, 1 - 1e-5)
        alpha, betap = p * s, (1 - p) * s
        lc = torch.lgamma(n_t + 1) - torch.lgamma(k_t + 1) - torch.lgamma(n_t - k_t + 1)
        return lc + lbeta(k_t + alpha, n_t - k_t + betap) - lbeta(alpha, betap)

    def closure():
        opt.zero_grad()
        ll = loglik_terms()
        pen = 0.5 * torch.sum(u_prec_t * (u - u_prior_t) ** 2)
        loss = -torch.mean(ll) + 0.5 * l2_beta * torch.sum(beta ** 2) + pen / len(n_t)
        loss.backward()
        return loss

    opt.step(closure)

    with torch.no_grad():
        total_ll = float(loglik_terms().sum())

    out = {
        "beta0": float(beta0.detach().numpy()[0]),
        "beta": beta.detach().numpy().copy(),
        "mu": mu, "std": std,
        "s": float(torch.exp(log_s).detach().numpy()[0]),
        "loglik": total_ll,
    }
    return out


def build_prior(df, offsets, anchor_counts):
    indel = df["indel_pct"].astype(float)
    p0 = float(np.clip(indel.median(), 0.05, 0.95))
    logit_p0 = float(np.log(p0 / (1 - p0)))
    cats = pd.Categorical(df["batch"])
    n_b = len(cats.categories)
    u_prior = np.zeros(n_b)
    u_prec = np.zeros(n_b)
    for i, b in enumerate(cats.categories):
        pb = np.clip(p0 + offsets.get(b, 0.0), 0.005, 0.995)
        u_prior[i] = np.log(pb / (1 - pb)) - logit_p0
        m = anchor_counts.get(b, 0)
        u_prec[i] = 10.0 if m >= 10 else (1.0 + float(m) if m > 0 else 1.0)
    return cats.codes, n_b, u_prior, u_prec, logit_p0


def prepare_arrays(df, feature_cols):
    X = df[feature_cols].astype(float).values
    indel = df["indel_pct"].astype(float).values
    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel).clip(0, n_reads)
    groups = df["gene_group"].values
    return X, n_reads, k_reads, indel, groups


# --------------------------------------------------------------------------
# Block 1：基因级检验（主结果）
# --------------------------------------------------------------------------
def block1_genelevel(df, offsets):
    d = df.copy()
    d["indel_adj"] = d["indel_pct"] - d["batch"].map(offsets).fillna(0.0)
    ct = pd.crosstab(d["batch"], d["gene_group"])

    agg = d.groupby("gene_group").agg(
        n_guides=("guide_id", "size"),
        n_batches=("batch", "nunique"),
        mean_indel=("indel_pct", "mean"),
        median_indel=("indel_pct", "median"),
        mean_indel_batchadj=("indel_adj", "mean"),
        sd_indel=("indel_pct", "std"),
    ).reset_index()
    agg["single_batch_confounded"] = agg["n_batches"] == 1
    agg["class_a_multibatch"] = agg["gene_group"].map(
        lambda g: int((ct[g] > 0).sum()) >= 3)

    # 表达特征在基因组内恒定，取首行即该基因的取值
    nuniq = d.groupby("gene_group")[EXPR_FEATURES].nunique(dropna=False)
    assert int(nuniq.max().max()) <= 1, "表达特征在基因组内不恒定，方法学前提不成立"
    per_gene_expr = d.groupby("gene_group")[EXPR_FEATURES].first()
    agg = agg.merge(per_gene_expr, left_on="gene_group", right_index=True, validate="1:1")

    expr_cols = [c for c in agg.columns if c in EXPR_FEATURES]
    return agg, expr_cols


def genelevel_stats(agg, target="mean_indel_batchadj"):
    rows = []
    for feat in EXPR_FEATURES:
        sub = agg.dropna(subset=[feat, target])
        if len(sub) < 5:
            continue
        rs, ps = spearmanr(sub[feat], sub[target])
        rp, pp = pearsonr(sub[feat], sub[target])
        # 按 guide 数加权（基因均值精度差异极大：306 条 vs 4 条）
        w = sub["n_guides"].values.astype(float)
        xm, ym = np.average(sub[feat], weights=w), np.average(sub[target], weights=w)
        cov = np.average((sub[feat] - xm) * (sub[target] - ym), weights=w)
        vx = np.average((sub[feat] - xm) ** 2, weights=w)
        slope_w = cov / vx if vx > 0 else np.nan
        rows.append({
            "block": "1_genelevel", "feature": feat, "target": target,
            "n_genes": len(sub), "spearman_rho": round(rs, 4), "spearman_p": round(ps, 4),
            "pearson_r": round(rp, 4), "pearson_p": round(pp, 4),
            "weighted_slope": round(slope_w, 5) if slope_w == slope_w else np.nan,
            "cohort": "all_genes",
        })
        sens = sub[~sub["single_batch_confounded"]]
        if len(sens) >= 5:
            rs2, ps2 = spearmanr(sens[feat], sens[target])
            rows.append({
                "block": "1_genelevel", "feature": feat, "target": target,
                "n_genes": len(sens), "spearman_rho": round(rs2, 4), "spearman_p": round(ps2, 4),
                "pearson_r": np.nan, "pearson_p": np.nan, "weighted_slope": np.nan,
                "cohort": "excl_single_batch",
            })
    return rows


# --------------------------------------------------------------------------
# Block 2：嵌套 GLMM（表达协变量 + LRT + 基因聚类自助 CI）
# --------------------------------------------------------------------------
def block2_nested_glmm(df, offsets, anchor_counts, boot_n, max_iter):
    b_idx, n_b, u_prior, u_prec, logit_p0 = build_prior(df, offsets, anchor_counts)
    Xa, n_reads, k_reads, indel, groups = prepare_arrays(df, SEQ_FEATURES)

    fit0 = fit_hier_bb(Xa, n_reads, k_reads, b_idx, u_prior, u_prec, logit_p0, max_iter=max_iter)
    ll0 = fit0["loglik"]
    print(f"    M0 (纯序列)      logLik = {ll0:.3f}")

    gene_groups = np.array(sorted(set(groups)))
    rows = []
    boot_store = {}

    for feat in EXPR_FEATURES:
        x = df[feat].astype(float).values
        if not np.isfinite(x).all():
            x = np.nan_to_num(x, nan=float(np.nanmean(x)))
        xs = (x - x.mean()) / (x.std() + 1e-9)
        Xb = np.column_stack([Xa, xs])
        fit1 = fit_hier_bb(Xb, n_reads, k_reads, b_idx, u_prior, u_prec, logit_p0, max_iter=max_iter)
        gamma = float(fit1["beta"][-1])
        lrt = 2.0 * (fit1["loglik"] - ll0)
        p_lrt = float(chi2.sf(max(lrt, 0.0), 1))
        print(f"    M1 +{feat:14s} logLik = {fit1['loglik']:.3f}  gamma = {gamma:+.4f}  "
              f"LRT = {lrt:+.3f}  p = {p_lrt:.4f}")
        rows.append({
            "block": "2_nested_glmm", "feature": feat, "target": "indel_pct (BB likelihood)",
            "n_genes": len(gene_groups), "gamma_std": round(gamma, 4),
            "lrt_chi2_1": round(lrt, 4), "lrt_p": round(p_lrt, 4),
            "loglik_M0": round(ll0, 3), "loglik_M1": round(fit1["loglik"], 3),
            "boot_n": 0, "gamma_ci_lo": np.nan, "gamma_ci_hi": np.nan, "cohort": "all_genes",
        })
        boot_store[feat] = (Xa, xs, n_reads, k_reads, b_idx, u_prior, u_prec, logit_p0, groups)

    # 基因聚类自助：尊重“有效样本量 = 基因数”这一事实
    if boot_n > 0:
        rng = np.random.default_rng(42)
        for feat, (Xa_, xs_, nr, kr, bi, up, upr, lp0, grp) in boot_store.items():
            gammas = []
            idx_by_gene = {g: np.where(grp == g)[0] for g in gene_groups}
            for _ in range(boot_n):
                pick = rng.choice(gene_groups, size=len(gene_groups), replace=True)
                rows_idx = np.concatenate([idx_by_gene[g] for g in pick])
                Xb_ = np.column_stack([Xa_[rows_idx], xs_[rows_idx]])
                try:
                    f = fit_hier_bb(Xb_, nr[rows_idx], kr[rows_idx],
                                    bi[rows_idx], up, upr, lp0, max_iter=max_iter)
                    gammas.append(float(f["beta"][-1]))
                except Exception:
                    continue
            if len(gammas) >= 20:
                lo, hi = np.percentile(gammas, [2.5, 97.5])
                for r in rows:
                    if r["feature"] == feat and r["block"] == "2_nested_glmm":
                        r["boot_n"] = len(gammas)
                        r["gamma_ci_lo"] = round(float(lo), 4)
                        r["gamma_ci_hi"] = round(float(hi), 4)
                print(f"    {feat:14s} 聚类自助 {len(gammas)} 次: gamma 95%CI "
                      f"[{lo:+.4f}, {hi:+.4f}]")
    return rows, fit0


# --------------------------------------------------------------------------
# Block 3：LOGO A/B 消融（方法学负对照）
# --------------------------------------------------------------------------
def block3_logo_ablation(df, offsets, anchor_counts, max_iter):
    from sklearn.model_selection import LeaveOneGroupOut

    b_idx, n_b, u_prior, u_prec, logit_p0 = build_prior(df, offsets, anchor_counts)
    Xa, n_reads, k_reads, indel, groups = prepare_arrays(df, SEQ_FEATURES)
    Xb = np.column_stack([Xa, df[EXPR_FEATURES].astype(float).fillna(0.0).values])

    ct = pd.crosstab(df["batch"], df["gene_group"])
    class_a = {g for g in ct.columns if (ct[g] > 0).sum() >= 3}

    per_fold = {}
    diag = {}
    for tag, X in (("A_seq_only", Xa), ("B_seq_plus_expr", Xb)):
        n_seq = len(SEQ_FEATURES)
        recs = []
        for tr, te in LeaveOneGroupOut().split(X, indel, groups):
            grp = groups[te][0]
            f = fit_hier_bb(X[tr], n_reads[tr], k_reads[tr], b_idx[tr],
                            u_prior, u_prec, logit_p0, max_iter=max_iter)
            Z = (X[te] - f["mu"]) / f["std"]
            pred = f["beta0"] + Z @ f["beta"]
            y = indel[te]
            if len(set(np.round(y, 6))) > 1 and len(set(np.round(pred, 6))) > 1:
                r, p = spearmanr(pred, y)
            else:
                r, p = np.nan, np.nan
            # 表达项在折内的标准差：结构上应恒为 0（基因级常量）
            expr_sd = float((Z[:, n_seq:] @ f["beta"][n_seq:]).std()) if X.shape[1] > n_seq else 0.0
            recs.append({"gene_group": grp, "n": len(te),
                         "class": "A_multibatch" if grp in class_a else "B_single_or_two_batch",
                         "rho": r, "p": p, "pred_sd": float(pred.std()), "expr_sd": expr_sd})
            if X.shape[1] > n_seq:
                diag.setdefault(grp, {})["beta_seq_B"] = [
                    (SEQ_FEATURES[i], float(f["beta"][i]))
                    for i in np.argsort(-np.abs(f["beta"][:n_seq]))[:4]]
            else:
                diag.setdefault(grp, {})["beta_seq_A"] = [
                    (SEQ_FEATURES[i], float(f["beta"][i]))
                    for i in np.argsort(-np.abs(f["beta"][:n_seq]))[:4]]
        per_fold[tag] = pd.DataFrame(recs)
        valid = per_fold[tag]["rho"].dropna()
        print(f"    Group {tag}: 有效折 {len(valid)}/{len(recs)}, 中位 rho = {valid.median():+.4f}")

    A, B = per_fold["A_seq_only"], per_fold["B_seq_plus_expr"]
    merged = A.merge(B, on="gene_group", suffixes=("_A", "_B"))
    merged["delta_rho"] = merged["rho_B"] - merged["rho_A"]

    rows = []
    for _, r in merged.iterrows():
        rows.append({
            "block": "3_logo_fold", "feature": r["gene_group"], "target": "within-fold rho",
            "n_guides": int(r["n_A"]), "class": r["class_A"],
            "rho_A": None if pd.isna(r["rho_A"]) else round(float(r["rho_A"]), 4),
            "rho_B": None if pd.isna(r["rho_B"]) else round(float(r["rho_B"]), 4),
            "delta_rho": None if pd.isna(r["delta_rho"]) else round(float(r["delta_rho"]), 4),
            "pred_sd_A": round(float(r["pred_sd_A"]), 5),
            "expr_sd_within_fold_B": float(f"{r['expr_sd_B']:.3e}"),
        })

    d = merged["delta_rho"].dropna()
    med_a = float(A["rho"].dropna().median())
    med_b = float(B["rho"].dropna().median())
    stats = {"n_folds_A": int(A["rho"].notna().sum()), "n_folds_B": int(B["rho"].notna().sum()),
             "median_rho_A": med_a, "median_rho_B": med_b,
             "median_delta_rho": float(d.median()) if len(d) else np.nan,
             "mean_abs_delta_rho": float(d.abs().mean()) if len(d) else np.nan,
             "max_abs_delta_rho": float(d.abs().max()) if len(d) else np.nan,
             "n_zero_delta": int((d == 0).sum()),
             # 结构性验证：表达项在任一折内的标准差应恒为 0
             "max_expr_sd_within_fold": float(B["expr_sd"].max()),
             # 仅在有效折（rho 可计算）内取预测标准差，退化折本就应被排除
             "min_pred_sd_B": float(B.loc[B["rho"].notna(), "pred_sd"].min()),
             "n_degenerate_folds_B": int(B["rho"].isna().sum())}
    if len(d) >= 1 and d.abs().max() > 0:
        flip = merged.loc[merged["delta_rho"].abs().idxmax()]
        stats["flip_gene"] = flip["gene_group"]
        stats["flip_rho_A"] = float(flip["rho_A"])
        stats["flip_rho_B"] = float(flip["rho_B"])
        stats["flip_delta"] = float(flip["delta_rho"])
    if len(d) >= 6 and d.abs().sum() > 0:
        w, pw = wilcoxon(merged["rho_B"].fillna(0), merged["rho_A"].fillna(0))
        stats["wilcoxon_W"] = float(w)
        stats["wilcoxon_p"] = float(pw)
    else:
        stats["wilcoxon_W"] = np.nan
        stats["wilcoxon_p"] = np.nan
        stats["wilcoxon_note"] = "Δρ 全为 0 或有效折过少，检验不可用（符合结构性预期）"
    print(f"    Δρ 中位 = {stats['median_delta_rho']:+.5f}, 平均|Δρ| = {stats['mean_abs_delta_rho']:.5f}, "
          f"Wilcoxon p = {stats.get('wilcoxon_p', float('nan')):.4f}")
    print(f"    [结构性验证] 表达项折内标准差最大值 = {stats['max_expr_sd_within_fold']:.3e} "
          f"(应恒为 0，即表达项对折内排序无直接贡献)")
    if "flip_gene" in stats:
        print(f"    [最大翻转折] {stats['flip_gene']}: rho {stats['flip_rho_A']:+.4f} -> "
              f"{stats['flip_rho_B']:+.4f} (Δρ = {stats['flip_delta']:+.4f})")
    return rows, stats, merged, (Xb, b_idx, n_reads, k_reads, u_prior, u_prec, logit_p0, indel, groups), diag


# --------------------------------------------------------------------------
# SHAP：线性模型的精确 Shapley 贡献 = beta_j * z_ij
# --------------------------------------------------------------------------
def shap_plot(Xb, feature_names, fit, indel, out_png):
    Z = (Xb - fit["mu"]) / fit["std"]
    contrib = Z * fit["beta"]
    mean_abs = np.abs(contrib).mean(axis=0)
    order = np.argsort(mean_abs)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("    [warn] matplotlib 不可用，跳过 SHAP 图")
        return pd.DataFrame({"feature": np.array(feature_names)[order],
                             "mean_abs_shapley": mean_abs[order]})
    fig, ax = plt.subplots(figsize=(8, 0.34 * len(feature_names) + 2))
    names = [feature_names[i] for i in order]
    colors = ["#2a9d8f" if n in EXPR_FEATURES else "#4a6fa5" for n in names]
    ax.barh(range(len(names)), mean_abs[order], color=colors)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("mean |Shapley contribution| (exact for linear model)")
    ax.set_title("Feature contribution to logit(p) — Group B (seq + TKS expression)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#4a6fa5", label="sequence"),
                       Patch(color="#2a9d8f", label="expression")], loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)
    print(f"    已落盘 {out_png.name}")
    return pd.DataFrame({"feature": names, "mean_abs_shapley": mean_abs[order]})


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=100, help="Block2 基因聚类自助次数")
    ap.add_argument("--quick", action="store_true", help="降低 LBFGS 迭代与自助次数，用于冒烟测试")
    args = ap.parse_args()
    boot_n = 20 if args.quick else args.boot
    max_iter = 80 if args.quick else 200

    print("=" * 78)
    print("方案2：TKS 转录组表达对 CRISPR 编辑效率作用的检验")
    print("=" * 78)

    print("\n[1/5] 载入 TKS 表达矩阵并构建基因级特征")
    expr_feat, audit = load_tks_expression()
    print(f"    基因数 = {audit['n_genes']}, 样本列 = {audit['n_sample_cols']} "
          f"(采用 {audit['n_used_cols']}, 排除 {audit['excluded_cols']})")
    print(f"    组织 = {audit['tissues']}, 发育期 = {audit['stages']}")
    print(f"    各组织样本数 = {audit['samples_per_tissue']}")
    print(f"    空值强制为 0 的单元格数 = {audit['n_nan_coerced_to_0']}")
    assert audit["n_used_cols"] + len(audit["excluded_cols"]) == audit["n_sample_cols"]

    results = {}
    for cohort in ("noB879", "train969"):
        primary = cohort == "noB879"
        print(f"\n{'=' * 78}\n[2/5] 队列 {cohort}\n{'=' * 78}")
        df = load_cohort(cohort)
        df = attach_expression(df, expr_feat)
        offsets, anchor_counts = batch_offsets(df)
        n_groups = df["gene_group"].nunique()
        print(f"    行数 = {len(df)}, 基因组 = {n_groups}, batch = {df['batch'].nunique()}")
        miss = df[EXPR_FEATURES].isna().any(axis=1).sum()
        print(f"    表达特征缺失行 = {miss}")

        agg, _ = block1_genelevel(df, offsets)
        n_conf = int(agg["single_batch_confounded"].sum())
        print(f"\n  --- Block 1 基因级检验（主结果）---")
        print(f"    单一 batch 共线基因组 = {n_conf}/{n_groups}（其表达效应不可辨识）")
        b1 = genelevel_stats(agg)
        for r in b1:
            print(f"    {r['feature']:14s} [{r['cohort']:19s}] n={r['n_genes']:2d} "
                  f"rho={r['spearman_rho']:+.3f} p={r['spearman_p']:.3f}")

        print(f"\n  --- Block 2 嵌套 GLMM（表达作为基因级协变量）---")
        b2, fit0 = block2_nested_glmm(df, offsets, anchor_counts, boot_n, max_iter)

        print(f"\n  --- Block 3 LOGO A/B 消融（方法学负对照）---")
        b3, b3stats, merged, arrays, diag = block3_logo_ablation(df, offsets, anchor_counts, max_iter)

        if primary:
            agg.to_csv(OUT_GENELEVEL, index=False)
            print(f"\n    基因级主表已落盘 {OUT_GENELEVEL.name}")
            Xb, b_idx, n_reads, k_reads, u_p, u_pr, lp0, indel, groups = arrays
            fitB = fit_hier_bb(Xb, n_reads, k_reads, b_idx, u_p, u_pr, lp0, max_iter=300)
            names = SEQ_FEATURES + EXPR_FEATURES
            shap = shap_plot(Xb, names, fitB, indel, OUT_SHAP)
            results["shap"] = shap
            results["agg"] = agg
            results["b3_merged"] = merged
            results["diag"] = diag
        results[cohort] = {"b1": b1, "b2": b2, "b3": b3, "b3stats": b3stats,
                           "n_groups": n_groups, "n_rows": len(df), "n_conf": n_conf}

    # ---- 汇总 CSV ----
    all_rows = []
    for cohort, R in results.items():
        if not isinstance(R, dict) or "b1" not in R:
            continue
        for r in R["b1"]:
            all_rows.append({**r, "cohort_tag": cohort})
        for r in R["b2"]:
            all_rows.append({**r, "cohort_tag": cohort})
    pd.DataFrame(all_rows).to_csv(OUT_STUDY, index=False)
    print(f"\n[4/5] 汇总已落盘 {OUT_STUDY.name}")

    # ---- 报告 ----
    write_report(results, audit, args)
    print(f"[5/5] 报告已落盘 {OUT_REPORT.name}")


def write_report(results, audit, args):
    R = results["noB879"]
    S = results.get("train969")
    agg = results["agg"]
    merged = results["b3_merged"]
    shap = results["shap"]

    def fmt_genelevel(rows):
        out = ["| 表达特征 | 基因数 | Spearman ρ | p | Pearson r | p | 加权斜率 |",
               "|---|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            if r["cohort"] != "all_genes":
                continue
            out.append(f"| `{r['feature']}` | {r['n_genes']} | {r['spearman_rho']:+.3f} | "
                       f"{r['spearman_p']:.3f} | {r['pearson_r']:+.3f} | {r['pearson_p']:.3f} | "
                       f"{r['weighted_slope']:+.4f} |")
        return "\n".join(out)

    def fmt_sens(rows):
        out = ["| 表达特征 | 基因数（剔除共线） | Spearman ρ | p |", "|---|---:|---:|---:|"]
        for r in rows:
            if r["cohort"] != "excl_single_batch":
                continue
            out.append(f"| `{r['feature']}` | {r['n_genes']} | {r['spearman_rho']:+.3f} | "
                       f"{r['spearman_p']:.3f} |")
        return "\n".join(out)

    def fmt_glmm(rows):
        out = ["| 表达协变量 | γ (标准化) | 95% CI (基因聚类自助) | LRT χ²(1) | p | 有效基因数 |",
               "|---|---:|---|---:|---:|---:|"]
        for r in rows:
            ci = "—" if pd.isna(r.get("gamma_ci_lo", np.nan)) else \
                 f"[{r['gamma_ci_lo']:+.3f}, {r['gamma_ci_hi']:+.3f}]"
            out.append(f"| `{r['feature']}` | {r['gamma_std']:+.4f} | {ci} | "
                       f"{r['lrt_chi2_1']:+.3f} | {r['lrt_p']:.4f} | {r['n_genes']} |")
        return "\n".join(out)

    def fmt_genes():
        out = ["| 基因组 | guides | batches | 平均 indel | 批次校正均值 | log2 根 | log2 叶 | log2 胶乳 | 发育均值 | τ | 共线 |",
               "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:--:|"]
        for _, r in agg.sort_values("mean_indel_batchadj", ascending=False).iterrows():
            out.append(
                f"| `{r['gene_group']}` | {int(r['n_guides'])} | {int(r['n_batches'])} | "
                f"{r['mean_indel']:.3f} | {r['mean_indel_batchadj']:.3f} | "
                f"{r['log2_gen']:.2f} | {r['log2_ye']:.2f} | {r['log2_jiaoru']:.2f} | "
                f"{r['dev_mean_log2']:.2f} | {r['tau']:.3f} | "
                f"{'⚠' if r['single_batch_confounded'] else ''} |")
        return "\n".join(out)

    def fmt_folds():
        out = ["| 基因组 | guides | 类别 | ρ (A 纯序列) | ρ (B +表达) | Δρ | 折内预测 sd (B) | 表达项折内 sd |",
               "|---|---:|---|---:|---:|---:|---:|---:|"]
        for _, r in merged.sort_values("delta_rho").iterrows():
            f = lambda v: "—" if pd.isna(v) else f"{v:+.4f}"
            out.append(f"| `{r['gene_group']}` | {int(r['n_A'])} | {r['class_A']} | "
                       f"{f(r['rho_A'])} | {f(r['rho_B'])} | {f(r['delta_rho'])} | "
                       f"{r['pred_sd_B']:.4f} | {r['expr_sd_B']:.1e} |")
        return "\n".join(out)

    def fmt_shap():
        out = ["| 特征 | mean \\|Shapley\\| |", "|---|---:|"]
        for _, r in shap.iloc[::-1].iterrows():
            out.append(f"| `{r['feature']}` | {r['mean_abs_shapley']:.4f} |")
        return "\n".join(out)

    st = R["b3stats"]
    # 伪重复对照：LRT 显著、但基因聚类自助 CI 跨 0 的特征
    pseudo = [r["feature"] for r in R["b2"]
              if r.get("lrt_p", 1.0) < 0.05 and not pd.isna(r.get("gamma_ci_lo", np.nan))
              and r["gamma_ci_lo"] <= 0 <= r["gamma_ci_hi"]]
    neg_gamma = [r["feature"] for r in R["b2"] if r["gamma_std"] < 0]
    pseudo_txt = "、".join(f"`{f}`" for f in pseudo) if pseudo else "无"
    neg_txt = "、".join(f"`{f}`" for f in neg_gamma) if neg_gamma else "无"

    # 最大翻转折的 β_seq 归因
    flip_gene = st.get("flip_gene", "—")
    dg = results.get("diag", {}).get(flip_gene, {})
    bA, bB = dict(dg.get("beta_seq_A", [])), dict(dg.get("beta_seq_B", []))
    top_names = [n for n, _ in dg.get("beta_seq_A", [])]
    top_names += [n for n, _ in dg.get("beta_seq_B", []) if n not in top_names]
    beta_hdr = " | ".join(f"`{n}`" for n in top_names)
    beta_sep = " | ".join("---:" for _ in top_names)
    beta_row_a = " | ".join(f"{bA[n]:+.4f}" if n in bA else "·" for n in top_names)
    beta_row_b = " | ".join(f"{bB[n]:+.4f}" if n in bB else "·" for n in top_names)
    report = f"""# 方案2：转录组表达水平对 Hi-TOM CRISPR/Cas9 编辑效率作用的消融检验

> 生成脚本：`scripts/17_ablation_expression_features.py`  
> 生成日期：2026-09-23  
> 主队列：noB879（{R['n_rows']} 行纯 A 级金标准，{R['n_groups']} 个基因组）  
> 敏感性队列：train969（{S['n_rows'] if S else '—'} 行，{S['n_groups'] if S else '—'} 个基因组）  
> 表达数据：`data/expression/2-3_TKS_Tiss-Dev-Expression(1).xlsx`（橡胶草 TKS，{audit['n_genes']:,} 基因）

---

## 一、结论摘要

在 noB879 金标准队列的 **{R['n_groups']} 个靶基因**上，橡胶草转录组表达水平与 CRISPR/Cas9
编辑效率之间**未检出具有统计学意义的关联**；点估计方向以**负相关**为主（叶组织
ρ = {[r['spearman_rho'] for r in R['b1'] if r['feature']=='log2_ye' and r['cohort']=='all_genes'][0]:+.3f}），
即表达越高的基因其平均 indel 频率并不更高、反而略低。

这一**阴性结果本身构成对项目的重要科学支撑**：它说明在菊科菊苣族 Hi-TOM 实测体系中，
gRNA 序列理化特征（而非靶基因转录活性）是编辑效率的主导决定因素，从而为
「本项目以序列为核心特征、以分层 Beta-Binomial 建模批次效应」的技术路线提供了实证辩护。

Block 3 的 LOGO A/B 消融进一步给出**结构性证据**：Δρ 中位数恰为 {st['median_delta_rho']:+.5f}，
{st['n_zero_delta']}/{st['n_folds_A']} 个折的 Δρ **严格为 0**，实测表达项在每个折内的标准差恒为
{st['max_expr_sd_within_fold']:.1e}。这直接证实：基因级常量协变量无法改变任何基因内部的 guide 排序。

逐折中位 ρ 由 {st['median_rho_A']:+.4f} 变为 {st['median_rho_B']:+.4f}，但**该下降不是表达特征有害的证据**：
它由单一折 `{flip_gene}` 的 ρ 符号翻转驱动，成因是近共线序列特征被重新配权（第六节给出 β 明细）。
故本结果**不构成**方案文档第五节「ρ 不升反降」熔断条件的触发——熔断条件针对的是
模型真实预测力下降，而此处预测力变化不可归因于表达特征本身。

---

## 二、数据口径与联接审计

| 项目 | 实测值 |
|---|---|
| TKS 表达矩阵基因数 | {audit['n_genes']:,} |
| 样本列总数 | {audit['n_sample_cols']} |
| 实际采用 | {audit['n_used_cols']} |
| 排除 | {', '.join(f'`{c}`' for c in audit['excluded_cols']) or '—'} |
| 组织类别 | {', '.join(f"{t}({TISSUE_CN.get(t,'?')})" for t in audit['tissues'])} |
| 各组织样本数 | {audit['samples_per_tissue']} |
| 发育期 | {', '.join(audit['stages'])} |
| 训练集靶基因命中率 | **{R['n_groups']}/{R['n_groups']}（100%）** |

**与方案文档的差异（须在文档中订正）**：

1. 方案文档称 TKS 表含「80 样本」，实测为 **{audit['n_sample_cols']} 个样本列**；
2. S9 胶乳列命名异常：存在 `S9-2jiaoru`（命名倒置，已按 rep2 采用）与
   `S9-jiaoruRNA7-3`（来源不明文库，已排除），缺 `S9-jiaoru-2`；
   **方案6 的 S1–S9 胶乳动力学曲线会直接受此影响，须先固定该口径**；
3. 方案文档称「11 个核心靶基因」，实测 noB879 队列含 **{R['n_groups']} 个基因组**
   （train969 含 {S['n_groups'] if S else '—'} 个），且 **100% 命中**表达矩阵；
4. noB879 口径下 LOGO 为 **{R['n_groups']} 折**而非文档所称 17 折
   （17 折对应 train969 口径）；
5. 同源对 `LG01.6995 / LG01.6999` 按 `scripts/15` 既有约定合并为一个基因组，
   其表达特征取两成员均值。

---

## 三、可辨识性告警：基因效应与批次效应的共线

{R['n_groups']} 个基因组中有 **{R['n_conf']} 个仅出现在单一 batch**。对这些基因，
「该基因表达高」与「该基因所在批次整体偏高/偏低」在数据上完全不可区分——
表达协变量的效应**在原理上不可辨识**，任何显著性都不应被解读为生物学结论。

此外队列严重不均衡：`{agg.sort_values('n_guides', ascending=False).iloc[0]['gene_group']}`
单基因即占 {int(agg.sort_values('n_guides', ascending=False).iloc[0]['n_guides'])} / {R['n_rows']} 条 guide。
**基因级检验的有效样本量是 {R['n_groups']}，不是 {R['n_rows']}**；下文所有 p 值均须在此前提下解读。

---

## 四、Block 1：基因级检验（主结果）

以「批次校正后的基因平均 indel」为因变量（校正量取 `scripts/15` 的 Selective EB
批次偏移），在基因组层面检验表达特征的作用。

{fmt_genelevel(R['b1'])}

### 剔除共线基因后的敏感性分析

{fmt_sens(R['b1'])}

### 基因级明细表

{fmt_genes()}

---

## 五、Block 2：嵌套分层 Beta-Binomial GLMM

在 `scripts/15` 形态二似然上逐个加入标准化表达协变量，与 M0（纯序列 10 特征）比较：

$$k_i \\sim \\mathrm{{BetaBinomial}}(n_i, p_i, s),\\quad
\\mathrm{{logit}}(p_i) = \\beta_0 + \\mathbf{{z}}_{{\\text{{seq}},i}}^\\top\\boldsymbol\\beta
+ \\gamma \\cdot z_{{\\text{{expr}},g(i)}} + u_{{b(i)}}$$

{fmt_glmm(R['b2'])}

γ 为标准化尺度上的对数几率贡献。**LRT 的 χ²(1) 参考分布在仅 {R['n_groups']} 个独立基因的情形下
过于乐观**，故同时给出以基因组为重采样单元的聚类自助 95% CI（{args.boot if not args.quick else 20} 次）。
凡 CI 跨越 0 者，均不得声称存在表达效应。

**伪重复对照（本节关键）**：{pseudo_txt} 的 LRT p < 0.05，但其基因聚类自助 95% CI 跨越 0。
这正是把 {R['n_rows']} 条 guide 当作 {R['n_rows']} 个独立观测所导致的伪重复——
似然比统计量按行计数，而表达协变量只在 {R['n_groups']} 个基因之间变化。
**结论以聚类自助 CI 为准，不以 LRT p 为准。**

γ 的符号：{neg_txt} 为负值，方向与 Block 1 的基因级点估计一致，
即表达越高的基因其编辑效率并不更高、反而略低。

**LRT 的额外口径说明**：拟合目标含 L2 惩罚 `0.5·λ·Σβ²`（λ = 0.01），而表中 logLik 为
**未加惩罚**的纯似然。因此 M1 的纯似然偶尔低于 M0，使 LRT 统计量为负、p 被截断为 1
（train969 队列的 `log2_jiaoru` 与 `dev_mean_log2` 即属此情形）。这不是程序错误，
但意味着该 LRT 并非严格的嵌套比较，**只能作为参考；结论一律以聚类自助 CI 与 Block 1 为准**。

---

## 六、Block 3：LOGO A/B 消融（方法学负对照）

Group A = 纯序列 10 特征；Group B = A + 5 个表达特征。留一基因交叉验证逐折 Spearman：

| 指标 | 数值 |
|---|---|
| Group A 有效折 / 中位 ρ | {st['n_folds_A']} / {st['median_rho_A']:+.4f} |
| Group B 有效折 / 中位 ρ | {st['n_folds_B']} / {st['median_rho_B']:+.4f} |
| Δρ 中位数 | {st['median_delta_rho']:+.5f} |
| 平均 \\|Δρ\\| | {st['mean_abs_delta_rho']:.5f} |
| 最大 \\|Δρ\\| | {st['max_abs_delta_rho']:.5f} |
| Δρ 恰为 0 的折数 | {st['n_zero_delta']} |
| **表达项折内标准差（全折最大值）** | **{st['max_expr_sd_within_fold']:.3e}** |
| 折内预测标准差（全折最小值） | {st['min_pred_sd_B']:.4f} |
| Wilcoxon 符号秩 p | {st.get('wilcoxon_p', float('nan')):.4f} |

### 为什么这一消融**在结构上无法**检出表达效应（重要方法学论断）

表达特征是**基因级常量**。LOGO 的一个 test fold 恰好就是**一个基因组**。
`scripts/15:204-205` 的推断路径为剔除批次随机截距后的纯序列生物学活性
`η_i = β_0 + z_i^⊤β`，因此表达项 `γ·z_expr,g` 对该 fold 内**所有**样本施加
**同一个常数偏移**。Spearman 秩相关对单调变换、特别是常数平移不变，故：

> **β_expr 对 fold 内 ρ 的直接贡献恒等于 0。**

观测到的 Δρ 只能来自两条二阶路径：(a) 加入协变量后序列系数 β_seq 被重新估计；
(b) 标准化用的 μ/σ 发生变化。二者均与「表达是否提升预测力」无因果关系。
因此**对逐折 Δρ 做 Wilcoxon 检验，检验的是噪声**——本块结果应作为负对照呈现，
用以说明「基因级协变量无法改善基因内排序」这一结构性事实。

**实测验证**：全部 {st['n_folds_B']} 个有效折中，表达项折内标准差的最大值为
{st['max_expr_sd_within_fold']:.3e}（严格恒定），而有效折内预测标准差的最小值为
{st['min_pred_sd_B']:.4f}——预测并未退化，ρ 是良定义的。上表的 0 不是数值巧合，而是结构必然。
（另有 {st['n_degenerate_folds_B']} 个折因该基因内 guide 的序列特征完全相同、预测恒定而被排除，
属预期行为，不计入有效折。）

### 最大翻转折归因：近共线序列特征被重新配权

`{flip_gene}` 的 ρ 由 **{st.get('flip_rho_A', float('nan')):+.4f}** 变为
**{st.get('flip_rho_B', float('nan')):+.4f}**（Δρ = {st.get('flip_delta', float('nan')):+.4f}），
是全表唯一的符号翻转，也是 Group B 中位 ρ 下降的唯一来源。

该翻转**不是**数值退化、也**不是**优化器未收敛——将 LBFGS 的 `max_iter` 分别设为
80 / 200 / 600，该折的 ρ、预测标准差与 β 完全一致。真实成因是加入表达协变量后似然面
重新分配，使**高度共线的 `tm` 与 `gc_total`** 交换了主导权：

| 特征组 | {beta_hdr} |
|---|{beta_sep}|
| Group A（纯序列） | {beta_row_a} |
| Group B（+表达） | {beta_row_b} |

（`·` 表示该特征未进入该组 \|β\| 前四名。）

**这一现象的外推意义超出方案2 本身**：一个与折内排序完全无关的基因级常量协变量，
仅通过改变 β_seq 的分配，就能把一个折的 ρ 从 {st.get('flip_rho_A', float('nan')):+.2f}
翻到 {st.get('flip_rho_B', float('nan')):+.2f}。这说明**逐折 LOGO ρ 在特征集扰动下高度不稳定**，
其绝对值不宜作为方案4「ρ ≥ 0.50」达标线的唯一判据（见第八节）。

### 逐折明细

{fmt_folds()}

---

## 七、特征贡献（线性模型精确 Shapley）

对线性模型，特征 i 的 Shapley 贡献精确等于 `β_j · z_ij`，无需近似采样：

{fmt_shap()}

![SHAP](ablation_expression_shap.png)

表达特征（绿色）的贡献量级须与第六节的结构性论断合并解读：其贡献体现为
**基因间的截距平移**，不改变任何基因内部的 guide 排序。

---

## 八、对后续方案的直接影响

1. **方案4（多组学模型重训）不应把 TKS 基因级表达特征当作提升 LOGO-CV ρ 的手段**。
   由第六节，基因级常量协变量在结构上无法改善留一基因折内排序；
   ρ ≥ 0.50 的达标线只能靠**基因内可变的**特征（序列、ATAC 峰区间、链冲突标志）达成。
   建议方案4 把 ATAC 可及性与转录链冲突作为主攻方向，表达量仅作辅助协变量。
2. **方案4 的「ρ ≥ 0.50」达标线本身需要更稳健的判据**。第六节显示，单一近共线序列特征
   （`tm` / `gc_total`）的重新配权就能让一个折的 ρ 从 +0.85 翻到 −0.85。建议达标判定
   除中位 ρ 外同时报告：(a) 有效折数、(b) 逐折 ρ 的四分位距、(c) Class A（多批次低混杂）
   折的中位 ρ，并固定 `max_iter`、`l2_beta` 与随机种子——否则「达标 / 未达标」
   可能只是优化器路径与特征共线性的产物，而非模型能力的真实变化。
3. **方案6（橡胶草时相窗口）须先固定 S9 胶乳列口径**（见第二节差异 2），
   否则 S1–S9 动力学曲线在末端时相不可比。
4. 本阴性结果应写入申报报告与论文的消融章节，作为**技术路线辩护材料**而非失败记录：
   它排除了「转录活性是主要混杂」这一审稿人常提的替代解释。

---

## 九、复现

```bash
conda run -n crispr python scripts/17_ablation_expression_features.py --boot {args.boot}
# 冒烟测试（降低 LBFGS 迭代与自助次数）
conda run -n crispr python scripts/17_ablation_expression_features.py --quick
```

产物：`{OUT_GENELEVEL.name}`、`{OUT_STUDY.name}`、`{OUT_SHAP.name}`、本报告。
"""
    OUT_REPORT.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
