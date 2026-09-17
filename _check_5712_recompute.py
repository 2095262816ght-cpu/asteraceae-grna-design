import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

xl = pd.ExcelFile(r"cs_pipeline\data\raw\hitom\sequencing_summary_20220130.xls")
d = xl.parse("USR-5712(2022.01.30)", header=None)
blocks = {}
cur=None
for _, r in d.iterrows():
    m = re.match(r"^(\d+)-ref", str(r[0]))
    if m: cur=m.group(1); blocks[cur]=[]; continue
    if cur and str(r[1]).strip().isdigit():
        blocks[cur].append([float(r[2]), str(r[3]), str(r[4]), str(r[5]), str(r[6])])

# 问题1: 1I(+a) 是编辑还是 artifact?
# 若是 artifact(参考与样本单倍型差异), 同遗传背景的所有样本应一致出现; 若是编辑, R1 分离群体中应有的样本有、有的没有
stat1i = []
for b, rows in blocks.items():
    t = sum(x[0] for x in rows)
    r1i = sum(x[0] for x in rows if "1I" in x[2])
    rwt = sum(x[0] for x in rows if x[2]=="WT")
    stat1i.append((b, r1i/t, rwt/t))
has1i = sum(1 for _,a,_ in stat1i if a>0.5)
mostly_wt = sum(1 for _,_,w in stat1i if w>0.5)
print(f"共{len(stat1i)}块: 右列1I占比>50%的块数={has1i}, 右列WT占比>50%的块数={mostly_wt}")
print("分布示例(块号, 1I占比, WT占比):", [(b, f'{a:.2f}', f'{w:.2f}') for b,a,w in stat1i[:12]])

# 问题2: 按切割点侧(右)重算 indel, 与表内现值对比
df = pd.ExcelFile(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx").parse("Sheet1")
df.columns = [str(c).strip() for c in df.columns]
sub = df[df["batch"].astype(str).str.strip()=="USR-5712"].reset_index(drop=True)
cur_vals = sorted(sub["indel_pct"].astype(float))
recomp = []
for b, rows in blocks.items():
    t = sum(x[0] for x in rows)
    rr = sum(x[0] for x in rows if x[2]!="WT")
    recomp.append(rr/t)
recomp.sort()
print("\n重算(右侧非WT) vs 表内现值: 前十后十")
print("重算:", [f"{v:.3f}" for v in recomp[:10]], "...", [f"{v:.3f}" for v in recomp[-6:]])
print("现值:", [f"{v:.3f}" for v in cur_vals[:10]], "...", [f"{v:.3f}" for v in cur_vals[-6:]])
import statistics
print(f"\n现值中位数={statistics.median(cur_vals):.4f}  重算中位数={statistics.median(recomp):.4f}")
print(f"现值≈0(<0.01)的行数={sum(1 for v in cur_vals if v<0.01)}  重算≈0的行数={sum(1 for v in recomp if v<0.01)}")

# 问题3: 左口径58/61吻合, 差的3行是哪些
left_vals = {}
for b, rows in blocks.items():
    t = sum(x[0] for x in rows)
    left_vals[b] = sum(x[0] for x in rows if x[1]!="WT")/t
mism = []
used = {}
lv = sorted(left_vals.items())
cv = sorted(cur_vals)
for (b, v), c in zip(lv, cv):
    if abs(v-c) > 0.001:
        mism.append((b, v, c))
print("\n左口径与现值不一致的块:", [(b, f'{v:.4f}', f'{c:.4f}') for b,v,c in mism])
