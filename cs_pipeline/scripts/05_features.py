"""05: 特征矩阵组装，产出 results/feature_matrix_0913.csv，骨架见 A3 节。"""
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN

df = pd.read_csv("results/scores_merged_0911.csv")
df["note"] = df["note"].fillna("")
df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)   # seq30 位置19-24 = PAM近端6nt
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
assert not df.drop(columns=["note"]).isna().any().any(), "特征矩阵存在 NA，查明原因后再冻结"  # note 为自由文本备注列，豁免
df.to_csv("results/feature_matrix_0913.csv", index=False)
df.to_csv("results/feature_matrix_0914.csv", index=False)
print(f"OK: {df.shape[0]} rows x {df.shape[1]} cols")
