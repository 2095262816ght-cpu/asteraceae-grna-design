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
probe = "GGATTGCTGCTGAGAAGGCC"
rc = revcomp(probe)
print("probe:", probe)
print("revcomp(probe):", rc)
pos = seq.find(rc)
while pos != -1:
    p1 = pos + 1
    down = seq[pos + 20:pos + 23]
    print(f"revcomp命中 @ LG01:{p1} -> 这相当于正链 {rc}+NGG, 下游3bp={down}")
    pos = seq.find(rc, pos + 1)

# 反方向理解：如果 guide=GGATTGCTGCTGAGAAGGCC 是"正链 20bp"，PAM 应该在它后面
p1 = seq.find(probe)
while p1 != -1:
    print(f"probe正链直接命中 @ {p1+1}, 下游3bp={seq[p1+20:p1+23]}")
    p1 = seq.find(probe, p1 + 1)
