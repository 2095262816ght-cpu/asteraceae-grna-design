import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

def load_genome():
    genome = {}
    cur = None
    with open(r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
        for line in f:
            if line.startswith(">"):
                cur = line[1:].split()[0]
                genome[cur] = []
            elif cur:
                genome[cur].append(line.strip().upper())
    return {k: "".join(v) for k, v in genome.items()}

def load_genes():
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
    return genes

def find_hits(genome, s):
    hits = []
    for ch, seq in genome.items():
        for probe, strand in [(s, "+"), (revcomp(s), "-")]:
            pos = seq.find(probe)
            while pos != -1:
                hits.append((ch, pos + 1, strand, pos))
                pos = seq.find(probe, pos + 1)
    return hits

def check(p, tag):
    import pandas as pd
    genome = load_genome()
    genes = load_genes()
    xl = pd.ExcelFile(p)
    total_bad = 0
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        if "gene-id" not in df.columns or "seq-20" not in df.columns:
            continue
        combos = {}
        for _, r in df.iterrows():
            g = str(r["gene-id"]).strip()
            s = str(r["seq-20"]).strip().upper()
            pam = str(r["pam"]).strip().upper()
            if re.fullmatch(r"[ACGT]{20}", s):
                combos.setdefault((g, s, pam), 0)
                combos[(g, s, pam)] += 1
        print(f"\n=== {tag} [{sh}] {len(df)}行, {len(combos)} 组唯一 guide ===")
        for (g, s, pam), n in sorted(combos.items()):
            gid = g if g.startswith("evm.model.") else f"evm.model.{g}"
            hits = find_hits(genome, s)
            info = genes.get(gid)
            ingene = []
            if info:
                gc, gs, ge, _ = info
                ingene = [h for h in hits if h[0] == gc and gs <= h[1] <= ge]
            # PAM
            pam_ok = []
            for (ch, p1, strand, pos) in hits:
                seq = genome[ch]
                if strand == "+":
                    if seq[pos + 20:pos + 23].upper() == pam:
                        pam_ok.append((ch, p1, strand))
                else:
                    if revcomp(seq[max(0, pos - 3):pos]).upper() == pam:
                        pam_ok.append((ch, p1, strand))
            status = []
            if not ingene:
                status.append("!!基因不命中!!")
                total_bad += 1
            if not pam_ok:
                status.append("PAM不匹配")
            print(f"  {'OK' if not status else '|'.join(status)} {g:20s} {s} pam={pam} 命中{len(hits)} 基因内{len(ingene)} PAM匹配{len(pam_ok)} x{n}行")
    return total_bad

files = [
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY12100-USR-23709-Hi-TOM-sequencing-result_processed_fixed.xlsx", "SY12100_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY13249-USR-25902-Hi-TOM-sequencing-result_processed_fixed.xlsx", "SY13249_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY2198-USR-4411-Hi-TOM-sequencing-result_processed_fixed.xlsx", "SY2198_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\sequencing_summary_20220130_processed_fixed.xlsx", "20220130_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY4070-USR-8145-Hi-TOM-sequencing_processed.xlsx", "SY4070(未改)"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\merged_T1T2_all-SY13345-USR-26162-Hi-TOM-sequencing-result_processed.xlsx", "SY13345(未改)"),
]
genome_cache = None
for p, tag in files:
    try:
        check(p, tag)
    except Exception as e:
        print(f"{tag} 读取失败: {e}")
