import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

# 1) 解析 sequencing_summary_20220130.xls 的 USR-5712 sheet, 按块复算左/右两侧非WT比例
xl = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
d = xl.parse("USR-5712(2022.01.30)", header=None)
blocks = {}   # block_name -> (left_nonWT, right_nonWT, total)
cur = None
for _, r in d.iterrows():
    s0 = str(r[0])
    m = re.match(r"^(\d+)-ref", s0)
    if m:
        cur = m.group(1); blocks[cur] = [0.0, 0.0, 0.0]
        continue
    if cur and str(r[1]).strip().isdigit():
        reads = float(r[2])
        blocks[cur][2] += reads
        if str(r[3]).strip() != "WT": blocks[cur][0] += reads
        if str(r[4]).strip() != "WT": blocks[cur][1] += reads
res = {}
for b,(l,rgt,t) in blocks.items():
    res[b] = (l/t if t else None, rgt/t if t else None)
print(f"共 {len(res)} 个块")
for b in sorted(res)[:8]:
    print(f"  块{b}: 左非WT={res[b][0]:.4f}  右非WT={res[b][1]:.4f}")

# 2) Sheet1 中 USR-5712 的 61 行 indel
df = pd.ExcelFile(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx").parse("Sheet1")
df.columns = [str(c).strip() for c in df.columns]
sub = df[df["batch"].astype(str).str.strip()=="USR-5712"].reset_index(drop=True)
print(f"\nSheet1 USR-5712 行数 = {len(sub)}")
indel = sorted(sub["indel_pct"].astype(float))

# 3) 匹配检验: 左口径 vs 右口径
left_vals  = sorted(v[0] for v in res.values() if v[0] is not None)
right_vals = sorted(v[1] for v in res.values() if v[1] is not None)
def match(a, b):
    if len(a)!=len(b): return -1, None
    diffs=[abs(x-y) for x,y in zip(a,b)]
    return sum(d<0.001 for d in diffs), max(diffs)
print("indel vs 左口径:", match(indel, left_vals), f"(左口径块数={len(left_vals)})")
print("indel vs 右口径:", match(indel, right_vals), f"(右口径块数={len(right_vals)})")
