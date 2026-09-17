import sys, io, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s): return s.translate(str.maketrans("ACGTacgt","TGCAtgca"))[::-1]

genome={}; cur=None
for line in open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta"):
    if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
    elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}
lg01 = genome["LG01"]

# 解析全部块
blocks = {}
cur=None
with open(r"cs_pipeline\data\raw\hitom\all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls", encoding="utf-8", errors="replace") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        m = re.match(r"^(\d+)-ref(CPT\d)", parts[0])
        if m: cur=m.group(1)+"-"+m.group(2); blocks[cur]=[]; continue
        if cur and len(parts)>=9 and parts[1].strip().isdigit():
            blocks[cur].append({"reads":int(parts[1]), "lt":parts[3], "rt":parts[4],
                                "lv":parts[5], "rv":parts[6], "ls":parts[7], "rs":parts[8]})

# 1) 找 WT 参考行确定方向与坐标(任一块)
for b, rows in blocks.items():
    for r in rows:
        if r["lt"]=="WT" and r["rt"]=="WT":
            lref = r["ls"].upper()
            i = lg01.find(lref); ori="+"
            if i<0: i=lg01.find(revcomp(lref)); ori="-"
            print(f"块{b} WT左ref 长{len(lref)}: LG01正链 {i+1 if i>=0 else '未命中'} 方向={ori}")
            break
    else:
        continue
    break

# 2) 收集所有块的缺失/插入变异串, 统计缺失中心
del_counter = Counter()
ins_counter = Counter()
for b, rows in blocks.items():
    for r in rows:
        for side in ["l","r"]:
            t, v = r[side+"t"], r[side+"v"]
            m = re.match(r"^(\d+)D$", t)
            if m and v and v!="-" and set(v)<=set("ACGT"):
                del_counter[v.upper()] += r["reads"]
            m = re.match(r"^(\d+)I$", t)
            if m and v and v!="-" and set(v)<=set("ACGT"):
                ins_counter[v.upper()] += r["reads"]
print("\n缺失变异 Top10 (reads加权):")
for v,c in del_counter.most_common(10): print(f"  删 {v} x{c}")
print("插入变异 Top5:")
for v,c in ins_counter.most_common(5): print(f"  插 {v} x{c}")

# 3) 以负链视角上下文定位缺失位置
ctx_minus = "ATGAGCCCGTAAGGATTGCTGCTGAGAAGGCCATGG"   # 正链 165462905-940 的负链视角
print("\n负链视角上下文:", ctx_minus)
for v,c in del_counter.most_common(5):
    pos = ctx_minus.find(v)
    print(f"  删 {v}: 在上下文中起始idx={pos} (reads×{c})")

# 4) 枚举负链上所有 NGG PAM 的候选 guide, 预测切割点
print("\n负链候选 guide (PAM=NGG, 距观测缺失中心越近越可信):")
for i in range(len(ctx_minus)-2):
    if ctx_minus[i+1]=="G" and ctx_minus[i+2]=="G":
        pam = ctx_minus[i:i+3]; proto = ctx_minus[i-20:i]
        if len(proto)==20:
            cut = i-3.5  # 切割点在 PAM 上游3-4bp 之间
            print(f"  PAM idx{i}={pam} protospacer={proto} 预测cut位于idx{cut}")
