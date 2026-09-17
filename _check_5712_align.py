import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

def revcomp(s): return s.translate(str.maketrans("ACGTacgt","TGCAtgca"))[::-1]

xl = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
d = xl.parse("USR-5712(2022.01.30)", header=None)

# 收集块统计 + 每块代表序列
blocks = {}
cur = None
for _, r in d.iterrows():
    m = re.match(r"^(\d+)-ref", str(r[0]))
    if m: cur = m.group(1); blocks[cur] = {"rows":[]}; continue
    if cur and str(r[1]).strip().isdigit():
        blocks[cur]["rows"].append((float(r[2]), str(r[3]), str(r[4]), str(r[7]), str(r[8])))

# 左非WT最高的块
stat = []
for b, dct in blocks.items():
    t = sum(x[0] for x in dct["rows"])
    l = sum(x[0] for x in dct["rows"] if x[1]!="WT")
    stat.append((l/t, b))
stat.sort(reverse=True)
print("左非WT Top5 块:", [(b, f"{v:.4f}") for v,b in stat[:5]])

# 看最高块(0.64/0.70)的变异构成
for v, b in stat[:2]:
    print(f"\n=== 块{b} 左非WT={v:.4f} ===")
    for reads, lt, rt, ls, rs in blocks[b]["rows"][:6]:
        print(f" reads={reads} 左={lt} 右={rt}")
        print(f"   L: {ls[:130]}")
        print(f"   R: {rs[:130]}")

# amplicon 参考(WT 行)定位到基因组
genome = {}
cur_chr = None
with open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"): cur_chr = line[1:].split()[0]; genome[cur_chr]=[]
        elif cur_chr: genome[cur_chr].append(line.strip().upper())
lg07 = genome["LG07"]

wt_row = [x for x in blocks["001"]["rows"] if x[1]=="WT" and x[2]=="WT"][0]
left_ref, right_ref = wt_row[3], wt_row[4]
# 完整 amplicon = left_ref + right_ref 的反向互补? 试两种拼法
amp = left_ref + revcomp(right_ref)
i = lg07.find(amp)
print(f"\namplicon(左ref+revcomp右ref) 正链命中: {i+1 if i>=0 else '无'}")
if i < 0:
    amp2 = left_ref + right_ref
    j = lg07.find(amp2)
    print("amplicon(左ref+右ref直接拼) 正链命中:", j+1 if j>=0 else "无")
    # 尝试找左ref
    k = lg07.find(left_ref); print("左ref 正链命中:", k+1 if k>=0 else "无")
    k2 = lg07.find(revcomp(left_ref)); print("revcomp(左ref) 正链命中:", k2+1 if k2>=0 else "无")
    k3 = lg07.find(right_ref); print("右ref 正链命中:", k3+1 if k3>=0 else "无")
    k4 = lg07.find(revcomp(right_ref)); print("revcomp(右ref) 正链命中:", k4+1 if k4>=0 else "无")
else:
    # 打印 cut site 附近的比对: 切割点 = PAM上游3bp (正链 109029070/071)
    cut_plus = 109029071  # 1-based
    offset = cut_plus - (i+1)  # 在 amp 中的位置
    print(f"切割点在 amplicon 展示方向的位置: {offset} / {len(amp)}")
    print(f"amplicon 左段长度={len(left_ref)}, 即切割点在{'左段' if offset < len(left_ref) else '右段'}")
    print("切割点附近 amplicon 序列:", amp[offset-30:offset+30])
