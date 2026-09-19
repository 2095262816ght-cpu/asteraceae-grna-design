# -*- coding: utf-8 -*-
"""最终对比: QC剔除后 4 种标签口径 (raw / 批内z / 批内rank / 锚定校正)
y 统一 round(6) 消除浮点尾差, 保证常数折判定一致"""
import numpy as np, pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

df = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
deep = pd.read_csv("results/scores_deepspcas9_merged_0918.csv")
crisp = pd.read_csv("results/scores_crispron_merged_0918.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
df["note"] = df["note"].fillna("")
df = df[~df["note"].str.contains("QC剔除")].copy()
df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
FEATS = [c for c in df.columns if c.startswith(("deepspcas9","crispron","gc_","pam_n_")) or c in ("tm","poly_t")]
HOMOLOG = {"EVM.MODEL.LG01.6995":"EVM.MODEL.LG01.6995/6999","EVM.MODEL.LG01.6999":"EVM.MODEL.LG01.6995/6999"}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)
X = df[FEATS].astype(float).values
groups = df["gene_group"].values
indel = df["indel_pct"].astype(float).round(6)

# 锚定校正
shared = df.groupby("seq20")["batch"].nunique()
shared = set(shared[shared >= 2].index)
gmed = df[df.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()
offsets = {}
for b, sub in df.groupby("batch"):
    s = sub[sub.seq20.isin(shared)]
    if len(s): offsets[b] = (s["indel_pct"] - s.seq20.map(gmed)).median()
y_anchor = (indel - df["batch"].map(offsets).fillna(0.0)).clip(0, 1).round(6)

yvars = {
  "raw":    (indel*100).round(6).values,
  "zscore": indel.groupby(df["batch"]).transform(lambda s:(s-s.mean())/(s.std(ddof=0) or 1.0)).round(6).values,
  "rank":   indel.groupby(df["batch"]).rank(pct=True).round(6).values,
  "anchor": (y_anchor*100).values,
}

def eval_label(y, name):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3,3,13)}, cv=cv, scoring="neg_mean_squared_error")
    gs.fit(X[tr], y[tr])
    pred = gs.best_estimator_.predict(X[te])
    rho, _ = spearmanr(pred, y[te])
    y_te = y[te]; q20, q80 = np.percentile(y_te, 20), np.percentile(y_te, 80)
    mask = (y_te <= q20) | (y_te >= q80)
    auc = roc_auc_score((y_te[mask]>=q80).astype(int), pred[mask]) if len(np.unique(y_te[mask]))>1 else np.nan
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3,3,13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        if len(set(y[te_i]))>1 and len(set(np.round(p_i,9)))>1:
            rhos.append(spearmanr(p_i, y[te_i])[0])
    med = float(np.median(rhos))
    print(f"[{name:7s}] test rho={rho:+.4f}  AUC={auc:.4f}  LOGO-CV中位rho={med:+.4f}  (有效折={len(rhos)})")
    return {"label":name, "spearman_rho_test":round(rho,4), "auc_test":round(auc,4), "rho_logo_cv_median":round(med,4)}

print(f"数据: QC剔除后 {len(df)} 行 / {len(set(groups))} 基因分组 / {df['batch'].nunique()} 批次")
comp = pd.DataFrame([eval_label(y, n) for n, y in yvars.items()])
comp.to_csv("results/model_comparison_qc_norm_0918.csv", index=False)
print()
print(comp.to_string(index=False))
print("\n参照: 旧数据基线(487行raw) LOGO-CV中位rho=0.414")
