# -*- coding: utf-8 -*-
"""rescore_demo_v21_nob879.py — 使用 2026-09-21 终版形态二生产模型 (noB879) 对 demo 候选库 19,839 条重打分

输入：demo/app_data.csv (含真实 deepspcas9_score 与 crispron_score)
模型：results/meta_model_hier_bb_nob879_0921.joblib
输出：写回 demo/app_data.csv，新增列 efficiency_score_v21_nob879
"""

import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from features_common import FEATURE_COLS, seq_features

APP_DATA = BASE / "demo" / "app_data.csv"
MODEL_PATH = BASE / "results" / "meta_model_hier_bb_nob879_0921.joblib"

print(f"载入模型: {MODEL_PATH}")
meta = joblib.load(MODEL_PATH)
assert isinstance(meta, dict) and "beta" in meta

print(f"载入候选数据: {APP_DATA}")
df = pd.read_csv(APP_DATA, dtype={"seq20": "string", "seq30": "string", "pam": "string"})
print(f"候选总数: {len(df)}")
assert len(df) == 19839

# 特征计算：9 个序列派生特征由 features_common.seq_features 单点定义（与生产训练同源）
feat_df = seq_features(df["seq30"])
feat_df["deepspcas9_score"] = df["deepspcas9_score"].astype(float)
feat_df["crispron_score"] = df["crispron_score"].astype(float)

assert list(meta["feature_cols"]) == FEATURE_COLS, \
    f"模型 feature_cols 与 features_common.FEATURE_COLS 不一致：{list(meta['feature_cols'])}"
X = feat_df[FEATURE_COLS].astype(float).values
Z = (X - meta["mu"]) / meta["std"]
logits = meta["beta0"] + np.dot(Z, meta["beta"])
probs = 1.0 / (1.0 + np.exp(-logits))
scores_v21 = np.clip(probs * 100.0, 0.0, 100.0).round(2)

df["efficiency_score_v21_nob879"] = scores_v21

# 备份与写入
bak = APP_DATA.with_suffix(".backup_20260921_pre_v21.csv")
if not bak.exists():
    pd.read_csv(APP_DATA).to_csv(bak, index=False)
    print(f"已创建备份: {bak}")

df.to_csv(APP_DATA, index=False)
print(f"成功写回 {APP_DATA}，新增列: efficiency_score_v21_nob879")
print("\n新打分分布统计 (0-100 相对排序活性指数):")
print(df["efficiency_score_v21_nob879"].describe().round(2).to_string())
