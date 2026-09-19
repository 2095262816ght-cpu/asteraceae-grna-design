# -*- coding: utf-8 -*-
"""m13_train_norm.py — QC剔除后三种标签口径的对比训练评估
在 merged_0918 数据上:
  raw  : 原始 indel_pct (x100, 与既往口径一致)
  z    : 批内 z-score
  rank : 批内 rank 分位数 [0,1]
评估: GroupShuffleSplit(42) 测试集 rho/AUC + LOGO-CV 中位 rho
"""
import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

SUFFIX = "merged_0918"

df = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
deep = pd.read_csv("results/scores_deepspcas9_merged_0918.csv")
crisp = pd.read_csv("results/scores_crispron_merged_0918.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
df["note"] = df["note"].fillna("")

# ---- QC 剔除 ----
n0 = len(df)
df = df[~df["note"].str.contains("QC剔除")].copy()
print(f"QC剔除: {n0} -> {len(df)} 行 (剔 {n0-len(df)})")

# ---- 特征 (同 05/13) ----
df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_"))
         or c in ("tm", "poly_t")]
HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
           "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)
assert not df[FEATS].isna().any().any()

X = df[FEATS].astype(float).values
groups = df["gene_group"].values

def eval_label(y, name):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups))
    assert len(set(groups[tr]) & set(groups[te])) == 0
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)},
                      cv=cv, scoring="neg_mean_squared_error")
    gs.fit(X[tr], y[tr])
    pred = gs.best_estimator_.predict(X[te])
    rho, _ = spearmanr(pred, y[te])
    y_te = y[te]
    q20, q80 = np.percentile(y_te, 20), np.percentile(y_te, 80)
    mask = (y_te <= q20) | (y_te >= q80)
    auc = roc_auc_score((y_te[mask] >= q80).astype(int), pred[mask]) if len(np.unique(y_te[mask])) > 1 else np.nan
    # LOGO
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)},
                           cv=cv_i, scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        if len(set(y[te_i])) > 1 and len(set(p_i)) > 1:
            rhos.append(spearmanr(p_i, y[te_i])[0])
    logo_med = float(np.nanmedian(rhos))
    print(f"[{name:6s}] 测试集基因={sorted(set(groups[te]))}")
    print(f"         test rho={rho:.4f}  AUC={auc:.4f}  LOGO-CV中位rho={logo_med:.4f}  (alpha={gs.best_params_['alpha']})")
    return {"label": name, "spearman_rho_test": round(rho, 4), "auc_test": round(auc, 4),
            "rho_logo_cv_median": round(logo_med, 4)}

y_raw = df["efficiency_norm"].astype(float).values   # = indel_pct*100
indel = df["indel_pct"].astype(float)
# 批内 z-score (批内 std=0 时全为 0)
z = indel.groupby(df["batch"]).transform(lambda s: (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) > 0 else 1.0))
# 批内 rank 分位数
rk = indel.groupby(df["batch"]).rank(pct=True)

results = []
results.append(eval_label(y_raw, "raw"))
results.append(eval_label(z.values, "z-score"))
results.append(eval_label(rk.values, "rank"))

comp = pd.DataFrame(results)
comp.to_csv("results/model_comparison_qc_norm_0918.csv", index=False)
print("\n=== 汇总 (QC剔除后 %d 行 / %d 基因分组) ===" % (len(df), len(set(groups))))
print(comp.to_string(index=False))
print("\n参照: 旧数据基线(487行) LOGO-CV中位rho=0.414")
print("Saved results/model_comparison_qc_norm_0918.csv")
