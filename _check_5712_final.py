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
genome = {k:"".join(v) for k,v in genome.items()}
lg07 = genome["LG07"]

xl = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
d = xl.parse("USR-5712(2022.01.30)", header=None)
rows = {}
cur=None
for _, r in d.iterrows():
    m = re.match(r"^(\d+)-ref", str(r[0]))
    if m: cur=m.group(1); rows[cur]=[]; continue
    if cur and str(r[1]).strip().isdigit():
        rows[cur].append([str(r[3]),str(r[4]),str(r[7]),str(r[8])])
amplicons = set()
for b in rows:
    m = None
# 块名
xl2 = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
names = []
for _, r in d.iterrows():
    m = re.match(r"^(\d+)-(.+)$", str(r[0]))
    if m: names.append(m.group(2))
print("5712 全部块所用参考:", set(names))

# 用块007的 WT 右参考 (干净) 做精确定位
wt_right = None
for lt, rt, ls, rs in rows["007"]:
    if rt == "WT":
        wt_right = rs.upper(); break
print("WT 右参考(展示方向):", wt_right)
rc = revcomp(wt_right)
i = lg07.find(rc)
print(f"revcomp(右参考) 命中正链 {i+1}..{i+len(rc)}")

# 展示方向右参考中变异热点 "CCTGA"
off = wt_right.find("CCTGA")
cut_display = off + 5   # CCTGA 之后
# 展示方向右参考是负链: 展示位置 p -> 正链坐标 = i+len(rc) - p
plus_at = i + len(rc) - off
print(f"热点 CCTGA 起始于正链约 {plus_at} 附近")
# 正链上该区间的序列
lo = i+1  # 1-based start
region = lg07[plus_at-30-1 : plus_at+30]
print("正链该区域(±30):", region)
# 负链(展示) 5'->3' 同区域
print("负链视角(±30):", revcomp(region))

# 推断负链 protospacer+PAM: 在展示方向, cut 在 CCTGA 之后; PAM 应在 cut 下游3bp处(展示方向 3')
# 展示方向序列: ...CCTGA AGG GAC... -> 若 PAM=AGG, protospacer = 上游20bp
p_idx = wt_right.find("CCTGAAGGG")
print("\n展示方向 热点上下文:", wt_right[p_idx-25:p_idx+15])
proto = wt_right[p_idx-25+5:p_idx+5]  # CCTGA结尾的20bp
print("推断负链 protospacer(展示=负链序列):", proto, " PAM=", wt_right[p_idx+5:p_idx+8])
# 基因组唯一性: 该 protospacer+PAM 在负链
full = proto + wt_right[p_idx+5:p_idx+8]
print("负链 protospacer+PAM =", full, " 其 revcomp 在正链命中次数:", lg07.count(revcomp(full)))

# 对比表内记录的 guide
print("\n表内记录 guide = GAAAATATTGAAAACATATA + TGG (正链 109029054-073)")
print("推断真实 guide =", proto, "+", wt_right[p_idx+5:p_idx+8], " (负链, 正链坐标约", i+len(rc)-(p_idx+8)+1, "..", i+len(rc)-(p_idx-20), ")")
