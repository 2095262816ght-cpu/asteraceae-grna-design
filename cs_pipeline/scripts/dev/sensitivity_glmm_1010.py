# -*- coding: utf-8 -*-
"""sensitivity_glmm_1010.py — 形态二 GLMM 两项诊断敏感性实验（只读诊断，不动生产模型与冻结指标）。

背景（2026-10-10 代码走查发现，登记见 CHANGELOG_0927.md 当日条目）
------------------------------------------------------------------
1. 先验泄漏：scripts/15 的 compute_batch_prior(df) 在**全量 879 行**上估计批次先验
   （锚点偏移用到 indel_pct），随后测试集与所有 LOGO 折拟合共用该先验——测试折标签
   经 u_prior 进入训练。本脚本以「折内重算先验」（每折只用训练行估计）对照现状，
   量化泄漏对指标的影响。
2. 过离散度 s：hier_bb_model 拟合值 0.632 被 clamp(1.0, 500) 顶回 1.0 才进似然
   （s=1 已是该参数化允许的过离散上限），且 clamp 截断梯度。本脚本以 s_floor=0.01
   放开下界重拟合，观察 s、beta 与指标变化。

设计：2×2（先验 {全量, 折内} × s_floor {1.0, 0.01}），其余与 scripts/15 完全一致
（同一队列、同一 GroupShuffleSplit(random_state=42)、同一 LOGO、同一 round(6) 有效折守卫）。

产物（诊断件，**非冻结指标**）：
    results/sensitivity_glmm_1010.csv        实验汇总（2×2 + 复现校验）
    results/sensitivity_glmm_folds_1010.csv  逐折对照（全量先验 vs 折内先验）

运行（cs_pipeline/ 下）：python scripts/dev/sensitivity_glmm_1010.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BASE_DIR = SCRIPTS_DIR.parent
for _p in (str(SCRIPTS_DIR), str(BASE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from features_common import FEATURE_COLS, load_cohort  # noqa: E402
from hier_bb_model import (  # noqa: E402
    compute_batch_prior,
    fit_hierarchical_selective_bb,
)

OUT_SUMMARY = BASE_DIR / "results" / "sensitivity_glmm_1010.csv"
OUT_FOLDS = BASE_DIR / "results" / "sensitivity_glmm_folds_1010.csv"
PRIOR_SCALE = 5.0


def load_xy(df):
    X = df[FEATURE_COLS].astype(float).values
    indel = df["indel_pct"].astype(float)
    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)
    return X, n_reads, k_reads, indel


def fit_predict(X, n, k, indel, tr_i, te_i, prior, s_floor):
    """用给定先验拟合训练折并对留出折输出纯序列活性（剔除 u_b），与 scripts/15 同式。"""
    b0, w, mu, std, s_raw = fit_hierarchical_selective_bb(
        X[tr_i], n[tr_i], k[tr_i],
        prior["batch_idx"], prior["n_batches"],
        prior["u_prior"], prior["u_prec"], prior["logit_p0"],
        prior_scale=PRIOR_SCALE, s_floor=s_floor,
    )
    Z = (X[te_i] - mu) / std
    pred = b0 + Z.dot(w)
    return pred, float(s_raw)


def valid_rho(pred, y):
    """scripts/15 同款 round(6) 有效折守卫 + Spearman。"""
    if len(set(np.round(y, 6))) > 1 and len(set(np.round(pred, 6))) > 1:
        r, p = spearmanr(pred, y)
        return float(r), float(p)
    return np.nan, np.nan


def run_logo(df, X, n, k, indel, groups, prior_mode, s_floor):
    """LOGO-CV。prior_mode: 'full'=全量先验（现状）, 'fold'=折内重算（无泄漏）。"""
    full_prior = compute_batch_prior(df) if prior_mode == "full" else None
    rows = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, indel, groups):
        if prior_mode == "full":
            prior = {
                **full_prior,
                "batch_idx": full_prior["batch_idx"][tr_i],
            }
        else:
            prior = compute_batch_prior(df.iloc[tr_i])
        pred, s_raw = fit_predict(X, n, k, indel, tr_i, te_i, prior, s_floor)
        y = indel.values[te_i]
        r, p = valid_rho(pred, y)
        rows.append({
            "gene_group": groups[te_i][0],
            "n_rows": len(te_i),
            "n_guides": int(len(set(df["seq20"].values[te_i]))),
            "rho": round(r, 4) if r == r else np.nan,
            "p_value": round(p, 4) if p == p else np.nan,
            "s_raw_last_fit": s_raw,
        })
    return pd.DataFrame(rows)


def run_test(df, X, n, k, indel, groups, prior_mode, s_floor):
    """20% 留出测试集（GroupShuffleSplit 与 scripts/15 逐位一致）。"""
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_idx, te_idx = next(gss.split(X, indel, groups))
    if prior_mode == "full":
        full = compute_batch_prior(df)  # 现状：含测试行
        prior = {**full, "batch_idx": full["batch_idx"][tr_idx]}
    else:
        prior = compute_batch_prior(df.iloc[tr_idx])  # 无泄漏：只用训练行
    pred, s_raw = fit_predict(X, n, k, indel, tr_idx, te_idx, prior, s_floor)
    y = indel.values[te_idx]
    r, p = valid_rho(pred, y)
    return r, p, s_raw


def main():
    df = load_cohort("noB879")
    X, n, k, indel = load_xy(df)
    groups = df["gene_group"].values
    print(f"队列 noB879: {len(df)} 行 / {df['seq20'].nunique()} 条 distinct guide / "
          f"{df['gene_group'].nunique()} 基因组 / {df['batch'].nunique()} 批次")

    ct = pd.crosstab(df["batch"], df["gene_group"])
    class_a = {g for g in ct.columns if len(ct[g][ct[g] > 0]) >= 3}

    designs = [
        ("E0_fullprior_sfloor1", "full", 1.0),
        ("E1_foldprior_sfloor1", "fold", 1.0),
        ("E2_fullprior_sfloor001", "full", 0.01),
        ("E3_foldprior_sfloor001", "fold", 0.01),
    ]

    summary, fold_tables = [], {}
    for name, prior_mode, s_floor in designs:
        folds = run_logo(df, X, n, k, indel, groups, prior_mode, s_floor)
        folds["class_a"] = folds["gene_group"].isin(class_a)
        fold_tables[name] = folds
        test_rho, test_p, _ = run_test(df, X, n, k, indel, groups, prior_mode, s_floor)
        valid = folds.dropna(subset=["rho"])
        med = valid["rho"].median()
        med_a = valid[valid["class_a"]]["rho"].median()
        med_b = valid[~valid["class_a"]]["rho"].median()
        summary.append({
            "experiment": name,
            "prior_mode": prior_mode,
            "s_floor": s_floor,
            "test_rho": round(test_rho, 4),
            "test_p": test_p,
            "logo_median_rho": round(med, 4),
            "classa_median_rho": round(med_a, 4),
            "classb_median_rho": round(med_b, 4),
            "valid_folds": f"{len(valid)}/{len(folds)}",
        })
        print(f"{name}: test rho={test_rho:+.4f} | LOGO median={med:+.4f} | "
              f"ClassA={med_a:+.4f} | valid {len(valid)}/{len(folds)}")

    # 全量重拟合：记录生效 s 与 beta 变化（s_floor 敏感性）
    beta_rows = []
    for name, prior_mode, s_floor in designs:
        prior = compute_batch_prior(df)
        b0, w, mu, std, s_raw = fit_hierarchical_selective_bb(
            X, n, k, prior["batch_idx"], prior["n_batches"],
            prior["u_prior"], prior["u_prec"], prior["logit_p0"],
            prior_scale=PRIOR_SCALE, s_floor=s_floor, max_iter=300,
        )
        beta_rows.append({
            "experiment": name, "s_raw": round(s_raw, 4),
            "s_effective": round(min(max(s_raw, s_floor), 500.0), 4),
            "beta0": round(b0, 4),
            **{f"beta_{c}": round(float(v), 4) for c, v in zip(FEATURE_COLS, w)},
        })
        print(f"{name} 全量重拟合: s_raw={s_raw:.4f} "
              f"(生效 {min(max(s_raw, s_floor), 500.0):.4f})")

    out = pd.DataFrame(summary)
    out.to_csv(OUT_SUMMARY, index=False)
    pd.DataFrame(beta_rows).to_csv(
        OUT_SUMMARY.with_name("sensitivity_glmm_beta_1010.csv"), index=False)

    # 逐折对照：E0（全量先验）vs E1（折内先验）
    cmp_df = fold_tables["E0_fullprior_sfloor1"][
        ["gene_group", "n_rows", "class_a", "rho"]].rename(columns={"rho": "rho_fullprior"})
    cmp_df = cmp_df.merge(
        fold_tables["E1_foldprior_sfloor1"][["gene_group", "rho"]].rename(
            columns={"rho": "rho_foldprior"}),
        on="gene_group")
    cmp_df["delta"] = (cmp_df["rho_foldprior"] - cmp_df["rho_fullprior"]).round(4)
    cmp_df.to_csv(OUT_FOLDS, index=False)

    print("\n汇总:", OUT_SUMMARY.relative_to(BASE_DIR))
    print("逐折:", OUT_FOLDS.relative_to(BASE_DIR))
    print("\n逐折对照（全量先验 vs 折内先验）:")
    print(cmp_df.to_string(index=False))


if __name__ == "__main__":
    main()
