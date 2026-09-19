# -*- coding: utf-8 -*-
"""11: 全量版 DeepSpCas9 打分（逻辑同 02，输入输出改全量文件）。"""
import pandas as pd
from genet.predict import SpCas9

df = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
pred = SpCas9().predict(df.seq30.tolist())
assert (pred["Target"].values == df.seq30.values).all(), "genet 输出顺序与输入不一致"
df["deepspcas9_score"] = pred["SpCas9"].values
assert df["deepspcas9_score"].notna().all()
df[["guide_id", "deepspcas9_score"]].to_csv("results/scores_deepspcas9_merged_0918.csv", index=False)
print(f"OK: {len(df)} rows -> results/scores_deepspcas9_merged_0918.csv")
