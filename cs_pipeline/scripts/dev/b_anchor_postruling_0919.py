# -*- coding: utf-8 -*-
"""b_anchor_postruling_0919.py — 老师 9.19 裁决后的锚定校正重算
裁决口径: QC剔除(350行) 之上, 整批剔除 USR-14333(疑T2代测序) 与 USR-22807(参照与基因型不配套), 其余保留。
同时采用计B round(6) 常数折守卫（冻结指标尘埃折整改口径）。
输出: results/b_anchor_postruling_0919.csv
"""
import numpy as np, pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

df = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
deep = pd.read_csv("results/scores_deepspcas9_merged_0918.csv")
crisp = pd.read_csv("results/scores_crispron_merged_0918.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
df["note"] = df["note"].fillna("")
n0 = len(df)
df = df[~df["note"].str.contains("QC剔除")].copy()
n_qc = len(df)
DROP_BATCH = ["USR-14333", "USR-22807"]
df = df[~df["batch"].isin(DROP_BATCH)].copy()
print(f"行数: {n0} -> QC剔除后 {n_qc} -> 整批剔除{DROP_BATCH}后 {len(df)}")

df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]
HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999", "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)
X = df[FEATS].astype(float).values
groups = df["gene_group"].values
indel = df["indel_pct"].astype(float)

shared = df.groupby("seq20")["batch"].nunique()
shared = set(shared[shared >= 2].index)
gmed = df[df.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()
offsets = {}
for b, sub in df.groupby("batch"):
    s = sub[sub.seq20.isin(shared)]
    if len(s):
        offsets[b] = (s["indel_pct"] - s.seq20.map(gmed)).median()
uncorr = [b for b in df["batch"].unique() if b not in offsets]
print(f"锚定 guide 数: {len(shared)}; 可校正批次: {len(offsets)}/{df['batch'].nunique()}; 不可校正: {uncorr}")
print("各批次偏移量:", {k: round(v, 3) for k, v in offsets.items()})
y_anchor = (indel - df["batch"].map(offsets).fillna(0.0)).clip(0, 1).values

def eval_label(y, name):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv, scoring="neg_mean_squared_error")
    gs.fit(X[tr], y[tr])
    rho, _ = spearmanr(gs.best_estimator_.predict(X[te]), y[te])
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        # round(6) 双侧常数折守卫（计B 9.19 整改口径）
        if len(set(np.round(y[te_i], 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
            rhos.append(spearmanr(p_i, y[te_i])[0])
    med = float(np.nanmedian(rhos))
    print(f"[{name:7s}] test rho={rho:.4f}  LOGO-CV中位rho={med:.4f}  有效折={len(rhos)}/{len(set(groups))}")
    return {"label": name, "n_rows": len(df), "test_rho": round(rho, 4),
            "logo_cv_median_rho": round(med, 4), "n_folds": len(rhos), "n_groups": len(set(groups))}

res = [eval_label((indel * 100).values, "raw"), eval_label(y_anchor * 100, "anchor")]
pd.DataFrame(res).to_csv("results/b_anchor_postruling_0919.csv", index=False)
print("Saved results/b_anchor_postruling_0919.csv")
