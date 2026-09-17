import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

genome = {}
cur=None
with open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
        elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}
lg01 = genome["LG01"]

# 表内记录
df = pd.ExcelFile(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx").parse("Sheet1")
df.columns = [str(c).strip() for c in df.columns]
sub = df[df["seq-20"].astype(str).str.strip()=="GGATTGCTGCTGAGAAGGCC"]
print("表内 GGATTGCTGCTGAGAAGGCC 行数:", len(sub))
for k, g in sub.groupby(["gene-id","pam","chrom","start","end","strand"]):
    print("  ", k, f"x{len(g)}", "indel:", sorted(set(g['indel_pct']))[:5], "...")

# 基因组正链上该区间的实际序列
lo = 165462900
region = lg01[lo-1:165462960]
print(f"\n正链 LG01:{lo}-165462960:")
print(region)
# 标记各位点
rec = "GGATTGCTGCTGAGAAGGCC"
alt = "CGTAAGGATTGCTGCTGAGA"
for name, probe in [("记录guide原样", rec), ("记录guide的revcomp", revcomp(rec)),
                    ("移位guide原样", alt), ("移位guide的revcomp", revcomp(alt))]:
    i = lg01.find(probe)
    print(f"{name} ({probe}) 正链命中: {i+1 if i>=0 else '无'}", end="")
    if i>=0:
        print(f"  下游3bp={lg01[i+20:i+23]}  上游3bp={lg01[i-3:i]}", end="")
    print()
# 负链视角展示
s, e = 165462905, 165462940
print(f"\n正链 {s}-{e}: {lg01[s-1:e]}")
print(f"负链视角  : {revcomp(lg01[s-1:e])}")
