import sys, io, re
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

# ---- 1. 载入 TKS 基因组各染色体 ----
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
print("染色体:", {k: len(v) for k, v in genome.items()})

# ---- 2. 解析 GFF3 基因坐标 ----
genes = {}
with open(r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-2_TKS.genome.gff3", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 9 or parts[2] != "gene":
            continue
        m = re.search(r"ID=([^;]+)", parts[8])
        if m:
            gid = m.group(1).replace("evm.TU.", "evm.model.")
            genes[gid] = (parts[0], int(parts[3]), int(parts[4]), parts[6])
print("基因数:", len(genes))

# ---- 3. 大表 23 组 guide 逐一回贴 ----
df = pd.ExcelFile(r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx").parse("Sheet1")
combos = {}
for _, r in df.iterrows():
    g = str(r["gene-id"]).replace("evm.model.", "")
    s = str(r["seq-20"]).strip().upper()
    chrom = str(r["chrom"]).strip()
    pam = str(r["pam"]).strip().upper()
    if re.fullmatch(r"[ACGT]{20}", s):
        combos.setdefault((g, s, pam, chrom, r["start "], r[" end"]), 0)
        combos[(g, s, pam, chrom, r["start "], r[" end"])] += 1

print("\n=== 全基因组回贴验证（23 组） ===")
bad = 0
for (g, s, pam, chrom, st, en), n in sorted(combos.items()):
    gid = f"evm.model.{g}"
    info = genes.get(gid)
    hits = []
    for ch, seq in genome.items():
        pos = seq.find(s)
        while pos != -1:
            hits.append((ch, pos + 1, "+"))  # 1-based
            pos = seq.find(s, pos + 1)
        rc = revcomp(s)
        pos = seq.find(rc)
        while pos != -1:
            hits.append((ch, pos + 1, "-"))
            pos = seq.find(rc, pos + 1)
    ingene = []
    if info:
        gc, gs, ge, gstrand = info
        for h in hits:
            if h[0] == gc and gs <= h[1] <= ge:
                ingene.append(h)
    ok = len(ingene) > 0
    # PAM 验证：在命中位置检查下游/上游 3bp
    pam_note = ""
    if hits:
        ch, p1, strand = hits[0]
        seq = genome[ch]
        if strand == "+":
            downstream = seq[p1 + 20 - 1:p1 + 20 - 1 + 3]
            pam_note = f"下游3bp={downstream}"
        else:
            upstream = seq[p1 - 1 - 3:p1 - 1]
            pam_note = f"上游3bp(revcomp)={revcomp(upstream)}"
    flag = "OK" if ok else "!!不在基因内!!"
    if not ok:
        bad += 1
    print(f"{flag} {g:12s} {s} pam={pam:3s} 记录chrom={chrom} | 全基因组命中{len(hits)}处: {hits} | 基因{gid}内命中: {ingene} | {pam_note} | x{n}行")

print(f"\n结论: {len(combos)} 组中 {bad} 组不在所标基因内")
