"""02: DeepSpCas9 打分（genet / TF2），产出 results/scores_deepspcas9_0910.csv。

降级方案1：替代 crisprScore（其 DeepSpCas9 环境为 py2.7+TF1.4.1，Windows 无法安装）。
输入 data/hitom_seq30_0909.csv（01 生成），输出列：guide_id, deepspcas9_score。
"""
import pandas as pd
from genet.predict import SpCas9

df = pd.read_csv("data/hitom_seq30_0909.csv")
pred = SpCas9().predict(df.seq30.tolist())  # 返回 DataFrame: Target, Spacer, SpCas9
assert (pred["Target"].values == df.seq30.values).all(), "genet 输出顺序与输入不一致"
df["deepspcas9_score"] = pred["SpCas9"].values
assert df["deepspcas9_score"].notna().all()
df[["guide_id", "deepspcas9_score"]].to_csv("results/scores_deepspcas9_0910.csv", index=False)
print(f"OK: {len(df)} rows -> results/scores_deepspcas9_0910.csv")
