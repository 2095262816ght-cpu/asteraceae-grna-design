"""B3 收尾：汇总 Cas-OFFinder 原始输出 -> results/offtarget_counts_0924.csv

输入：results/offtarget_raw_0924.txt（Cas-OFFinder v2.4.1 输出，tab 分隔，列：
    guide_pattern(seq20+NNN), chrom, pos, site_seq, strand, mismatch）
输出列约定（对齐《分工详案》B3：guide_id + 三档脱靶计数）：
    guide_id
    exact_match_count      = 错配数 == 0 的位点数（即基因组内完全匹配位点）
    offtarget_count_mis1   = 1 <= 错配数 <= 1 的脱靶位点数
    offtarget_count_mis2   = 1 <= 错配数 <= 2
    offtarget_count_mis3   = 1 <= 错配数 <= 3
（脱靶计数不含完全匹配本身，与 demo/app_data.csv 列含义一致）
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "results/offtarget_raw_0924.txt"
CAND = BASE / "data/demo_nlr50_candidates.csv"
OUT = BASE / "results/offtarget_counts_0924.csv"

raw = pd.read_csv(
    RAW, sep="\t", header=None,
    names=["guide_pattern", "chrom", "pos", "site_seq", "strand", "mismatch"],
    dtype={"guide_pattern": "string"},
)
raw["seq20"] = raw["guide_pattern"].str[:20]

exact = raw[raw.mismatch == 0].groupby("seq20").size().rename("exact_match_count")
off = raw[raw.mismatch >= 1]
mis1 = off[off.mismatch <= 1].groupby("seq20").size().rename("offtarget_count_mis1")
mis2 = off[off.mismatch <= 2].groupby("seq20").size().rename("offtarget_count_mis2")
mis3 = off[off.mismatch <= 3].groupby("seq20").size().rename("offtarget_count_mis3")

cand = pd.read_csv(CAND, usecols=["guide_id", "seq20"])
# seq20 存在少量重复（285 条）：Cas-OFFinder 输入模式为 seq20+NNN，
# 相同 seq20 的脱靶谱必然相同，按 seq20 多对一映射与工具口径一致。
out = cand.merge(pd.concat([exact, mis1, mis2, mis3], axis=1), on="seq20", how="left")
for c in ("exact_match_count", "offtarget_count_mis1", "offtarget_count_mis2", "offtarget_count_mis3"):
    out[c] = out[c].fillna(0).astype(int)

out[["guide_id", "exact_match_count", "offtarget_count_mis1",
     "offtarget_count_mis2", "offtarget_count_mis3"]].to_csv(OUT, index=False)

n = len(out)
print(f"guides: {n}")
print(f"raw sites: {len(raw)}")
print(f"exact==0 guides (无完全匹配, 异常信号): {(out.exact_match_count == 0).sum()}")
print(f"mis3==0 guides (无脱靶): {(out.offtarget_count_mis3 == 0).sum()}")
print(f"mis3 median/mean/max: {out.offtarget_count_mis3.median()}/{out.offtarget_count_mis3.mean():.1f}/{out.offtarget_count_mis3.max()}")
assert n == len(cand)
