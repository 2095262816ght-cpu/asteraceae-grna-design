import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

# 基因组
genome={}; cur=None
for line in open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta"):
    if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
    elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}
lg01 = genome["LG01"]

# 解析 8145 结果(制表符文本)
blocks = {}
cur=None
with open(r"cs_pipeline\data\raw\hitom\all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls", encoding="utf-8", errors="replace") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        m = re.match(r"^(\d+)-ref(CPT\d)", parts[0])
        if m:
            cur = m.group(1)+"-"+m.group(2); blocks[cur]=[]; continue
        if cur and len(parts)>=9 and parts[1].strip().isdigit():
            blocks[cur].append([float(parts[2]), parts[4], parts[5], parts[8], parts[9] if len(parts)>9 else ""])

print("总块数:", len(blocks))
# 取一个 refCPT1 块看方向与变异位置
for bname in ["097-CPT1"]:
    rows = blocks[bname]
    print(f"\n=== 块{bname} 共{len(rows)}行 ===")
    for reads, lt, rt, ls, rs in rows[:6]:
        print(f" reads={reads} 左={lt} 右={rt}")
        print(f"   L:{ls[:120]}")
        print(f"   R:{rs[:120]}")
    # 找WT参考
    for reads, lt, rt, ls, rs in rows:
        if lt=="WT" and rt=="WT":
            lref, rref = ls, rs
            break
    else:
        lref, rref = rows[0][3], rows[0][4]
    print("\nWT参考 左:", lref)
    print("WT参考 右:", rref)
    for nm, s in [("左ref原样", lref), ("revcomp(左ref)", revcomp(lref)), ("右ref原样", rref), ("revcomp(右ref)", revcomp(rref))]:
        i = lg01.find(s.upper())
        print(f"{nm} -> LG01正链: {i+1 if i>=0 else '未命中'}")
