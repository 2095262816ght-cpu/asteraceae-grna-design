# -*- coding: utf-8 -*-
"""b_anchor_161_0921.py — 16.1 口径锚定/LOGO 重跑（进展报告 6.5 待办#1）

代码路径与 b_anchor_final_0919.py 完全一致（同种子/同特征/同 round(6) 常数折守卫），
仅人群换成 16.1 版口径，便于与 0919 数字直接对比：
  ruling1005 = 9.19裁决保留 ∩ 可打分（应精确复现 raw -0.2623 / anchor -0.0785）
  train969   = 16.1 训练集（处理状态=保留）
  noB879     = train969 − B级90行(TKS_0668属裁决剔除,不在训练集)（量化"跳台账临时转正"的影响，15版说明遗留事项2）
输出: results/b_anchor_161_0921.csv
运行: cd cs_pipeline && python scripts/dev/b_anchor_161_0921.py
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

XLSX = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"
a = pd.read_excel(XLSX, sheet_name="全部打分")
gid_all = a["guide-id"].astype(str)
pop_ruling = set(gid_all[a["9.19裁决"] == "保留"])
pop_train = set(gid_all[a["处理状态"] == "保留"])
pop_noB = set(gid_all[(a["处理状态"] == "保留") & (a["等级"] != "B")])
print("人群(表级): ruling=%d train=%d noB=%d" % (len(pop_ruling), len(pop_train), len(pop_noB)))
assert len(pop_train) == 969 and len(pop_noB) == 879

base = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
base = base.merge(pd.read_csv("results/scores_deepspcas9_merged_0918.csv"), on="guide_id", validate="1:1")
base = base.merge(pd.read_csv("results/scores_crispron_merged_0918.csv"), on="guide_id", validate="1:1")
base["guide_id"] = base["guide_id"].astype(str)

HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
           "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}


def build(df):
    df = df.copy()
    df["note"] = df["note"].fillna("")
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
    indel = df["indel_pct"].astype(float)
    y_anchor = (indel - df["batch"].map(offsets).fillna(0.0)).clip(0, 1).values
    return df, indel, y_anchor, offsets


def feats(df):
    return [c for c in df.columns
            if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]


def eval_label(X, y, groups, name, pop, n):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X, y, groups))
    cv = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
    gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv,
                      scoring="neg_mean_squared_error")
    gs.fit(X[tr], y[tr])
    rho = spearmanr(gs.best_estimator_.predict(X[te]), y[te])[0]
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, groups):
        cv_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
        g_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i,
                           scoring="neg_mean_squared_error")
        g_i.fit(X[tr_i], y[tr_i])
        p_i = g_i.best_estimator_.predict(X[te_i])
        # round(6) 双侧常数折守卫（计B 9.19 整改口径）
        if len(set(np.round(y[te_i], 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
            rhos.append(spearmanr(p_i, y[te_i])[0])
    med = float(np.nanmedian(rhos))
    print(f"[{pop:11s}|{name:6s}] n={n} test_rho={rho:.4f} LOGO中位rho={med:.4f} 有效折={len(rhos)}/{len(set(groups))}")
    return {"population": pop, "label": name, "n_rows": n, "test_rho": round(rho, 4),
            "logo_cv_median_rho": round(med, 4), "n_folds": len(rhos), "n_groups": len(set(groups))}


res = []
for pop, gids in [("ruling1005", pop_ruling), ("train969", pop_train), ("noB879", pop_noB)]:
    df = base[base.guide_id.isin(gids)]
    df, indel, y_anchor, offsets = build(df)
    X = df[feats(df)].astype(float).values
    groups = df["gene_group"].values
    print(f"== {pop}: n={len(df)} 基因组={len(set(groups))} 批次={df['batch'].nunique()} 可锚定批次={len(offsets)}")
    res.append(eval_label(X, (indel * 100).values, groups, "raw", pop, len(df)))
    res.append(eval_label(X, y_anchor * 100, groups, "anchor", pop, len(df)))

out = pd.DataFrame(res)
out.to_csv("results/b_anchor_161_0921.csv", index=False)
print("\n" + out.to_string())
print("Saved results/b_anchor_161_0921.csv")
