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

def pam_check(s, pam):
    out = []
    for ch, seq in genome.items():
        for probe, strand in [(s, "+"), (revcomp(s), "-")]:
            pos = seq.find(probe)
            while pos != -1:
                p1 = pos + 1
                if strand == "+":
                    downstream = seq[pos + 20:pos + 23]
                    if downstream.upper() == pam.upper():
                        out.append((ch, p1, strand))
                else:
                    upstream = revcomp(seq[max(0, pos - 3):pos])
                    if upstream.upper() == pam.upper():
                        out.append((ch, p1, strand))
                pos = seq.find(probe, pos + 1)
    return out

cases = [
    ("LG02.4820", "AACATGGTTCGAGTTCAAGA", "CCA"),
    ("LG02.4820", "AACATGGTTCGAGTTCAAGA", "TGG"),
    ("LG07.3296", "GAAAATATTGAAAACATATA", "TGG"),
    ("LG07.3296", "GAAAATATTGAAAACATATA", "AGG"),
    ("LG01.6995", "GGATTGCTGCTGAGAAGGCC", "TGG"),
    ("LG01.6995", "GGATTGCTGCTGAGAAGGCC", "ATG"),
]
for g, s, pam in cases:
    hits = pam_check(s, pam)
    print(f"{g} {s} PAM={pam}: 带匹配PAM的命中 = {hits}")

# 原始未修复 TTCAAG 序列归属
print("\n--- TTCAAGTTCTAAGTAATCCT 全基因组命中（任意PAM） ---")
s = "TTCAAGTTCTAAGTAATCCT"
for ch, seq in genome.items():
    for probe, strand in [(s, "+"), (revcomp(s), "-")]:
        pos = seq.find(probe)
        while pos != -1:
            p1 = pos + 1
            if strand == "+":
                downstream = seq[pos + 20:pos + 23]
                print(f"{ch}:{p1}({strand}) 下游3bp={downstream}")
            else:
                upstream = revcomp(seq[max(0, pos - 3):pos])
                print(f"{ch}:{p1}({strand}) 上游3bp(revcomp)={upstream}")
            pos = seq.find(probe, pos + 1)
