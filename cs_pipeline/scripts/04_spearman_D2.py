"""04: D2 迁移可行性——两模型打分 vs efficiency_norm 的 Spearman ρ，骨架见 A2 节。

efficiency_norm 为 F1 表自带列（生A 已做的批次内百分位），一律不得用 indel_pct 重算。
"""
import pandas as pd
from scipy.stats import spearmanr

df = pd.read_csv("results/scores_merged_0911.csv")

for col in ["deepspcas9_score", "crispron_score"]:
    rho, p = spearmanr(df[col], df["efficiency_norm"])
    print(f"{col}: Spearman rho = {rho:.3f}, p = {p:.2e}")
