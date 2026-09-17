import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

genome = {}
cur=None
with open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
        elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}
lg07 = genome["LG07"]

# 负链视角热点区序列(与WT右参考一致): 取正链 109028860..109028940 的 revcomp
plus = lg07[109028860-1:109028940]
minus = revcomp(plus)
print("正链 109028860-109028940 :", plus)
print("负链 5'->3' 同区         :", minus)

# 在负链上枚举 NGG PAM, 预测切割点 (PAM 5'端上游3bp处, 即负链视角 cut = PAM起始-3/-4之间)
print("\n负链上的 NGG PAM 候选 (cut 应落在观测 indel 中心):")
for i in range(len(minus)-2):
    if minus[i+1]=="G" and minus[i+2]=="G":
        pam = minus[i:i+3]
        proto = minus[i-20:i]
        # 负链视角位置 i 对应正链坐标: minus[j] 对应正链 109028940 - j
        pam_plus_end = 109028940 - i          # PAM 最右(负链3')对应正链坐标
        proto_plus = (109028940-(i-1), 109028940-(i-20))  # protospacer 正链区间(高,低)
        cut_plus = 109028940 - (i-3)
        print(f"  PAM={pam} (负链视角idx{i}) protospacer(-链)={proto}  正链 {proto_plus[1]}..{proto_plus[0]}  预测cut≈正链{cut_plus}")

# 观测 indel 中心: 16D 删除 "TCAGGATGCCTGAAGG"
j = minus.find("TCAGGATGCCTGAAGG")
lo, hi = 109028940-(j+15), 109028940-j
print(f"\n16D 删除段 正链 {lo}..{hi} (中心≈{(lo+hi)//2})")
j5 = minus.find("AGGAC")
print("5D 'AGGAC' 候选位置(正链):", [ (109028940-(k+4), 109028940-k) for k in [j5, minus.find('AGGAC', j5+1)] if k>=0 ])

# 唯一性: 负链 protospacer GAAAATGTCAGGATGCCTGA+AGG 在全基因组
probe = "GAAAATGTCAGGATGCCTGA"  # 负链
cnt = sum(s.count(revcomp(probe)) for s in genome.values())
cnt2 = sum(s.count(probe) for s in genome.values())
print(f"\nprotospacer(-链) GAAAATGTCAGGATGCCTGA: 作为负链靶点在基因组出现 {cnt} 次, 正链直接出现 {cnt2} 次")
# 表内记录 guide 的切割点处 (109029070) 与热点距离
print("表内靶点切割点 109029070 vs 热点中心 ~109028900: 相距约", 109029070-109028900, "bp")
