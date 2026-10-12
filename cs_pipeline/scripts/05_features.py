"""05: 特征矩阵组装，产出 results/feature_matrix_0913.csv，骨架见 A3 节。"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.features_common import seq_features  # noqa: E402

df = pd.read_csv("results/scores_merged_0911.csv")
df["note"] = df["note"].fillna("")
# 特征语义单点定义在 core.sequence_spec（种子区切片、Tm/GC 口径、PAM one-hot 4 列），
# 此处只经 seq_features 适配器取值，不再自持第二份推导。
df = pd.concat([df, seq_features(df.seq30)], axis=1)
assert not df.isna().any().any(), "特征矩阵存在 NA，查明原因后再冻结"
df.to_csv("results/feature_matrix_0913.csv", index=False)
df.to_csv("results/feature_matrix_0914.csv", index=False)
print(f"OK: {df.shape[0]} rows x {df.shape[1]} cols")
