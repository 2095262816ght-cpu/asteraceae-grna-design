import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

# 1) 最新版表中 USR-5712 批的记录
df = pd.ExcelFile(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx").parse("Sheet1")
df.columns = [str(c).strip() for c in df.columns]
sub = df[df["batch"].astype(str).str.strip() == "USR-5712"]
print(f"USR-5712 共 {len(sub)} 行")
cols = ["gene-id","seq-20","pam","chrom","start","end","strand"]
for k, grp in sub.groupby(["gene-id","seq-20","pam","chrom","start","end","strand"]):
    print(" ", k, f"x{len(grp)}", "indel集合:", sorted(set(grp["indel_pct"])))

# 2) 基因组两个方向搜索该 guide
genome = {}
cur = None
with open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"):
            cur = line[1:].split()[0]; genome[cur] = []
        elif cur:
            genome[cur].append(line.strip().upper())
genome = {k: "".join(v) for k, v in genome.items()}

seq = str(sub["seq-20"].iloc[0]).strip().upper()
print(f"\nguide(表内记录) = {seq}")
print(f"revcomp        = {revcomp(seq)}")
for ch, gseq in genome.items():
    for probe, ori in [(seq, "表内序列直接在正链上"), (revcomp(seq), "表内序列的反向互补在正链上(即表内序列位于负链)")]:
        pos = gseq.find(probe)
        while pos != -1:
            p1 = pos + 1
            down = gseq[pos+20:pos+23]      # 正链下游 3bp
            up   = gseq[max(0,pos-3):pos]   # 正链上游 3bp
            print(f"{ch}:{p1} [{ori}]")
            print(f"   正链下游3bp = {down}  (若表内序列在正链, 这是PAM: {'合法NGG' if len(down)==3 and down[1:]=='GG' else '非NGG'})")
            rc_up = revcomp(up)
            print(f"   正链上游3bp = {up} ->  revcomp = {rc_up}  (若表内序列在负链, 这是PAM: {'合法NGG' if len(rc_up)==3 and rc_up[1:]=='GG' else '非NGG/CCN视角: 正链上看是 '+up})")
            pos = gseq.find(probe, pos+1)
