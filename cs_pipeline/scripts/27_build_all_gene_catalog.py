"""Build full gene catalog + top-100 candidates per gene from scored_genome parts."""
from collections import Counter
from pathlib import Path

import pandas as pd

base = Path(r"D:\lifesciencechallenge\cs_pipeline")
parts = sorted((base / "results" / "scored_genome").glob("part_*.csv"))
print("loading parts...", len(parts), flush=True)

usecols = [
    "guide_id", "gene_id", "chrom", "start", "end", "strand", "seq20", "pam",
    "region_type", "seq30", "efficiency_score", "deepspcas9_score",
    "crispron_score", "crispron_source", "gc_total", "tm",
]
counts = Counter()
df_list = []
for i, p in enumerate(parts):
    d = pd.read_csv(p, usecols=usecols)
    counts.update(d["gene_id"].value_counts().to_dict())
    df_list.append(d)
    if (i + 1) % 100 == 0:
        print("read", i + 1, flush=True)

all_df = pd.concat(df_list, ignore_index=True)
print("all", len(all_df), "genes", all_df.gene_id.nunique(), flush=True)

top = (
    all_df.sort_values(["gene_id", "efficiency_score"], ascending=[True, False])
    .groupby("gene_id", sort=False)
    .head(100)
)
print("top", len(top), flush=True)
top_path = base / "results" / "lettuce_all_genes_top100_candidates.csv"
top.to_csv(top_path, index=False)
print("wrote", top_path, flush=True)

gff_genes = pd.read_csv(base / "results" / "lettuce_all_genes_gff.csv")
gff_genes["candidate_count"] = gff_genes["gene_id"].map(counts).fillna(0).astype(int)
gff_genes["g_chrom_norm"] = gff_genes["g_chrom"].str.replace(
    r"Chr0?(\d+)", lambda m: f"Chr{int(m.group(1)):02d}", regex=True
)
outg = base / "results" / "lettuce_all_genes_catalog.csv"
gff_genes.to_csv(outg, index=False)
print("wrote", outg, "genes", len(gff_genes), "with_cand", int((gff_genes.candidate_count > 0).sum()), flush=True)
print(gff_genes.head(3).to_string(), flush=True)
