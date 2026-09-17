import sys, io, re
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

genome = {}
cur = None
with open(r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"):
            cur = line[1:].split()[0]
            genome[cur] = []
        elif cur:
            genome[cur].append(line.strip().upper())
genome = {k: "".join(v) for k, v in genome.items()}

# 扫描 LG02.4820 基因区所有 NGG/CCN 20bp guide
def scan_guides(region):
    res = []
    for i in range(len(region) - 22):
        w = region[i:i + 23]
        if w[21:23] == "GG":
            res.append((i, w[:20], "+", w[20:23]))
        rc = revcomp(w)
        if rc[21:23] == "GG":
            res.append((i, rc[:20], "-", rc[20:23]))
    return res

ch = genome["LG02"]
gene_start, gene_end = 147964454, 147967112
region = ch[gene_start - 1:gene_end]
gs = scan_guides(region)
print(f"LG02.4820 基因区共 {len(gs)} 个 NGG/CCN guide")
targets = ["AACATGGTTCGAGTTCAAGA", "TTCAAGTTCTAAGTAATCCT"]
for t in targets:
    hits = [(gene_start + i, s, d, p) for i, s, d, p in gs if s == t or revcomp(s) == t]
    print(t, "->", hits)

# 大表中 AACATG 的 10 行
df = pd.ExcelFile(r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx").parse("Sheet1")
sub = df[df["seq-20"] == "AACATGGTTCGAGTTCAAGA"]
print("\n=== 大表 AACATGGTTCGAGTTCAAGA 的 10 行 ===")
print(sub[[" guide-id", "gene-id", "seq-20", "pam", "chrom", "start ", " end", "batch", " indel_pct", "备注"]].to_string())

# SY12100 fixed 分表
p2 = r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY12100-USR-23709-Hi-TOM-sequencing-result_processed_fixed.xlsx"
xl = pd.ExcelFile(p2)
for sh in xl.sheet_names:
    d = xl.parse(sh)
    if "seq-20" in d.columns:
        m = d[d["seq-20"] == "AACATGGTTCGAGTTCAAGA"]
        print(f"\n=== SY12100_fixed [{sh}] AACATG 行: {len(m)} ===")
        print(m.head(10).to_string())
