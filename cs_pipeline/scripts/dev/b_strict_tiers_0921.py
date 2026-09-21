# -*- coding: utf-8 -*-
"""b_strict_tiers_0921.py — 从严剔除五档方案的量化评估（用户 0921 问询）
T0=969现行 / T1去B级 / T2再去双gRNA / T3再去indel饱和 / T4再去更正行 / T5只留guide确定+原登记
每档输出: 行数、distinct guide(seq20)、基因组数、单guide基因数、批次数、锚定LOGO中位rho、有效折
评估框架与 b_anchor_161_0921.py 完全一致（同特征/同种子/同round(6)守卫）。
运行: cd cs_pipeline && python scripts/dev/b_strict_tiers_0921.py
"""
import sys

import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

a = pd.read_excel("data/1_Hi-results-16.1-efficiency-20260921.xlsx", sheet_name="全部打分")
base = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv("results/scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv("results/scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

tr = a[a["处理状态"] == "保留"].copy()
tr["gid"] = tr["guide-id"].astype(str)
is_B = tr["等级"] == "B"
is_dual = tr["判定依据"].astype(str).str.contains("双gRNA")
is_corr = tr["置信分"] == 85
is_a80 = tr["置信分"] == 80
indel = pd.to_numeric(tr["indel_pct"], errors="coerce")
is_sat = indel >= 0.999

tiers = {
    "T0_现行969": tr["gid"],
    "T1_去B级": tr.loc[~is_B, "gid"],
    "T2_再去双gRNA": tr.loc[~is_B & ~is_dual, "gid"],
    "T3_再去饱和indel": tr.loc[~is_B & ~is_dual & ~is_sat, "gid"],
    "T4_再去更正行": tr.loc[~is_B & ~is_dual & ~is_sat & ~is_corr, "gid"],
    "T5_只留确定+登记": tr.loc[~is_B & ~is_dual & ~is_sat & ~is_corr & ~is_a80, "gid"],
}
print("剔除增量: B级=%d 双gRNA=%d 饱和indel=%d 更正=%d A80候选=%d (相互有重叠)"
      % (is_B.sum(), is_dual.sum(), is_sat.sum(), is_corr.sum(), is_a80.sum()))

HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
           "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}


def build(df):
    df = df.copy()
    df["gc_total"] = df.seq20.map(gc_fraction)
    df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
    df["tm"] = df.seq20.map(Tm_NN)
    df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
    df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
    df["gene_group"] = df["gene_id"].replace(HOMOLOG)
    shared = df.groupby("seq20")["batch"].nunique()
    shared = set(shared[shared >= 2].index)
    gmed = df[df.seq20.isin(shared)].groupby("seq20")["indel_pct"].median()
    offsets = {}
    for b, sub in df.groupby("batch"):
        s = sub[sub.seq20.isin(shared)]
        if len(s):
            offsets[b] = (s["indel_pct"] - s.seq20.map(gmed)).median()
    ind = df["indel_pct"].astype(float)
    y_anchor = (ind - df["batch"].map(offsets).fillna(0.0)).clip(0, 1).values
    return df, ind, y_anchor, offsets


def feats(df):
    return [c for c in df.columns
            if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]


def eval_anchor(X, y, groups):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr_i, te_i = next(gss.split(X, y, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv,
                      scoring="neg_mean_squared_error")
    gs.fit(X[tr_i], y[tr_i])
    test_rho = spearmanr(gs.best_estimator_.predict(X[te_i]), y[te_i])[0]
    rhos = []
    for a_i, b_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[a_i])))).split(X[a_i], y[a_i], groups[a_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i,
                           scoring="neg_mean_squared_error")
        g_i.fit(X[a_i], y[a_i])
        p_i = g_i.best_estimator_.predict(X[b_i])
        if len(set(np.round(y[b_i], 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
            rhos.append(spearmanr(p_i, y[b_i])[0])
    return test_rho, float(np.nanmedian(rhos)) if rhos else np.nan, len(rhos)


rows = []
for name, gids in tiers.items():
    d = base[base.guide_id.isin(set(gids))]
    d, ind, y_anchor, offsets = build(d)
    X = d[feats(d)].astype(float).values
    groups = d["gene_group"].values
    per_gene = d.groupby("gene_group")["seq20"].nunique()
    t_rho, logo, n_folds = eval_anchor(X, y_anchor * 100, groups)
    rows.append(dict(tier=name, n_rows=len(d), n_guides=d.seq20.nunique(),
                     n_genes=len(set(groups)), single_guide_genes=int((per_gene == 1).sum()),
                     n_batches=d.batch.nunique(), anchored_batches=len(offsets),
                     test_rho=round(t_rho, 4), anchor_logo=round(logo, 4),
                     valid_folds=f"{n_folds}/{len(set(groups))}"))
    print(rows[-1])

out = pd.DataFrame(rows)
out.to_csv("results/b_strict_tiers_0921.csv", index=False)
print("\n" + out.to_string())
print("Saved results/b_strict_tiers_0921.csv")
