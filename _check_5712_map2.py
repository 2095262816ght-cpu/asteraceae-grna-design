import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd, re

def revcomp(s): return s.translate(str.maketrans("ACGTacgt","TGCAtgca"))[::-1]

genome = {}
cur = None
with open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"): cur = line[1:].split()[0]; genome[cur]=[]
        elif cur: genome[cur].append(line.strip().upper())
genome = {k: "".join(v) for k, v in genome.items()}
lg07 = genome["LG07"]

xl = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
d = xl.parse("USR-5712(2022.01.30)", header=None)
# 块007 有 WT 左/右参考行 (右非WT=0.0941 的那块); 也取块001
rows = {}
cur=None
for _, r in d.iterrows():
    m = re.match(r"^(\d+)-ref", str(r[0]))
    if m: cur=m.group(1); rows[cur]=[]; continue
    if cur and str(r[1]).strip().isdigit():
        rows[cur].append([str(r[3]),str(r[4]),str(r[7]),str(r[8])])

# 找一条左WT参考 和 右WT参考
left_ref = right_ref = None
for b in ["007","001","002"]:
    for lt, rt, ls, rs in rows[b]:
        if lt=="WT" and left_ref is None: left_ref = ls
        if rt=="WT" and right_ref is None: right_ref = rs
print("左ref:", left_ref[:60], "...", len(left_ref))
print("右ref:", right_ref[:60], "...", len(right_ref))

for name, s in [("左ref原样", left_ref), ("revcomp(左ref)", revcomp(left_ref)),
                ("右ref原样", right_ref), ("revcomp(右ref)", revcomp(right_ref))]:
    i = lg07.find(s.upper())
    print(f"{name} -> LG07 正链位置: {i+1 if i>=0 else '未命中'}")

# 右ref 中的变异热点 CCTGAaGGG: 定位在正链上的坐标
for probe_name, probe in [("右ref原样中的CCTGAGGG区", None)]:
    pass
i = lg07.find(right_ref.upper())
if i >= 0:
    # 右ref 在正链 i+1 起; 找 'CCTGA' 在右ref中的偏移
    off = right_ref.upper().find("CCTGA")
    print(f"\n右ref 起始(正链1-based) = {i+1}; 'CCTGA' 在右ref偏移 {off} -> 正链位置 {i+1+off}")
    print("切割点应在正链 109029070/071 (PAM 109029074-076 上游3bp)")
    print(f"右ref变异热点距切割点: {abs((i+1+off) - 109029070)} bp")
