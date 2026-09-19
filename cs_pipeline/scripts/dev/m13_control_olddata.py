# -*- coding: utf-8 -*-
"""对照B: 旧数据(487行)单独用三种标签口径评估"""
import numpy as np, pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut
import sys; sys.stdout.reconfigure(encoding='utf-8', errors='replace')

df = pd.read_csv("data/hitom/hitom_seq30_full_0916.csv")
deep = pd.read_csv("results/scores_deepspcas9_full_0916.csv")
crisp = pd.read_csv("results/scores_crispron_full_0916.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
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
indel = df["indel_pct"].astype(float)

def eval_label(y, name):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3,3,13)}, cv=cv, scoring="neg_mean_squared_error")
    gs.fit(X[tr], y[tr])
    rho, _ = spearmanr(gs.best_estimator_.predict(X[te]), y[te])
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3,3,13)}, cv=cv_i, scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        if len(set(y[te_i]))>1 and len(set(p_i))>1:
            rhos.append(spearmanr(p_i, y[te_i])[0])
    print(f"[{name:6s}] test rho={rho:.4f}  LOGO-CV中位rho={np.nanmedian(rhos):.4f}")

eval_label((indel*100).values, "raw")
z = indel.groupby(df["batch"]).transform(lambda s: (s-s.mean())/(s.std(ddof=0) if s.std(ddof=0)>0 else 1.0))
eval_label(z.values, "z-score")
rk = indel.groupby(df["batch"]).rank(pct=True)
eval_label(rk.values, "rank")
