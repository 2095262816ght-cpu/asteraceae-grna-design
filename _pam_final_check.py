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

# 检查所有非 TGG/AGG/CGG 的 PAM
import pandas as pd
df = pd.ExcelFile(r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx").parse("Sheet1")
combos = {}
for _, r in df.iterrows():
    g = str(r["gene-id"]).replace("evm.model.", "")
    s = str(r["seq-20"]).strip().upper()
    pam = str(r["pam"]).strip().upper()
    if re.fullmatch(r"[ACGT]{20}", s):
        combos[(g, s, pam)] = combos.get((g, s, pam), 0) + 1

print("=== 所有 guide 的 PAM 精确复核（负链取上游3bp revcomp，正链取下游3bp） ===")
for (g, s, pam), n in sorted(combos.items()):
    hits = []
    for ch, sq in genome.items():
        for probe, strand in [(s, "+"), (revcomp(s), "-")]:
            pos = sq.find(probe)
            while pos != -1:
                if strand == "+":
                    real = sq[pos + 20:pos + 23].upper()
                else:
                    real = revcomp(sq[max(0, pos - 3):pos]).upper()
                hits.append((ch, pos + 1, strand, real))
                pos = sq.find(probe, pos + 1)
    match = [h for h in hits if h[3] == pam]
    flag = "OK " if match else ("NGG类但PAM记录不同 " if any(h[3][1:] == "GG" for h in hits) else "!!非NGG!! ")
    print(f"{flag} {g:12s} {s} 记录PAM={pam} 实际={[ (h[0],h[1],h[2],h[3]) for h in hits]} x{n}")
