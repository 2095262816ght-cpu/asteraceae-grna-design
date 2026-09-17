import sys, io, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s): return s.translate(str.maketrans("ACGTacgt","TGCAtgca"))[::-1]

blocks = {}
cur=None
with open(r"cs_pipeline\data\raw\hitom\all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls", encoding="utf-8", errors="replace") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        m = re.match(r"^(\d+)-ref(CPT\d)", parts[0])
        if m: cur=m.group(1)+"-"+m.group(2); blocks[cur]=[]; continue
        if cur and len(parts)>=9 and parts[1].strip().isdigit():
            blocks[cur].append({"reads":int(parts[1]), "lt":parts[3], "ls":parts[7].upper()})

# 每个 amplicon 各取一条 WT 左 read 作参考(用最长公共前后缀定位变异)
def variant_interval(ref, seq):
    """返回 (start, end, 类型, 内容): ref[start:end] 被替换为 seq 中对应段"""
    p = 0
    while p < min(len(ref), len(seq)) and ref[p]==seq[p]: p += 1
    s = 0
    while s < min(len(ref)-p, len(seq)-p) and ref[len(ref)-1-s]==seq[len(seq)-1-s]: s += 1
    return p, len(ref)-s, seq[p:len(seq)-s] if len(seq)-s>p else ""

for amp in ["CPT1","CPT2"]:
    ref = None
    for b, rows in blocks.items():
        if not b.endswith(amp): continue
        for r in rows:
            if r["lt"]=="WT":
                ref = r["ls"]; break
        if ref: break
    if not ref:
        print(f"{amp}: 无WT参考行"); continue
    print(f"\n=== {amp} WT参考(长{len(ref)}): {ref}")
    # 统计变异区间(reads 加权), 只看 indel
    intervals = Counter()
    total = 0
    for b, rows in blocks.items():
        if not b.endswith(amp): continue
        for r in rows:
            if r["lt"]=="WT": continue
            if re.search(r"[DI]", r["lt"]):
                st, en, sub = variant_interval(ref, r["ls"])
                intervals[(st, en)] += r["reads"]
            total += r["reads"]
    print("indel 变异区间 Top8 (ref坐标, 左闭右开, reads数):")
    for (st,en),c in intervals.most_common(8):
        print(f"  [{st},{en}) 删{en-st}bp x{c}   参考该段={ref[st:en] if en>st else '-'} 前后={ref[max(0,st-5):st]}|{ref[en:en+5]}")
