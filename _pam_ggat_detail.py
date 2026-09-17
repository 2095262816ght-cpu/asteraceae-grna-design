import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

genome = {}
cur = None
with open(r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"):
            cur = line[1:].split()[0]
            genome[cur] = []
        elif cur:
            genome[cur].append(line.strip().upper())
genome = {k: "".join(v) for k, v in genome.items()}

seq = genome["LG01"]
for pos, strand in [(165462909, "-"), (165502827, "-")]:
    idx = pos - 1
    window = seq[idx - 6:idx + 25]
    up3 = revcomp(seq[idx - 3:idx])
    down3 = seq[idx + 20:idx + 23]
    print(f"LG01:{pos}({strand}) 窗口={window} 上游3bp(revcomp)={up3} 下游3bp={down3}")

# 正链上这段序列
probe = "GGATTGCTGCTGAGAAGGCC"
p1 = seq.find(probe)
if p1 != -1:
    print(f"\n正链直接命中 @ {p1+1}: 下游3bp={seq[p1+20:p1+23]}")
p2 = seq.find(revcomp(probe))
if p2 != -1:
    print(f"revcomp命中 @ {p2+1}: 上游3bp(revcomp)={revcomp(seq[p2-3:p2])}")
    # 看更宽的窗口
    print("  revcomp窗口:", seq[p2-5:p2+25])
