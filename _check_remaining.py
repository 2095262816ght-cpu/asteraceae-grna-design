import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

genome={}; cur=None
for line in open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta"):
    if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
    elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}

df = pd.ExcelFile(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx").parse("Sheet1")
df.columns = [str(c).strip() for c in df.columns]
guides = {}
for _, r in df.iterrows():
    s = str(r["seq-20"]).strip().upper()
    if len(s)!=20 or set(s)-set("ACGT"): continue
    key = (str(r["gene-id"]).replace("evm.model.",""), s, str(r["pam"]).strip().upper(),
           str(r["chrom"]).strip(), int(r["start"]))
    guides.setdefault(key, 0); guides[key] += 1

print("=== 每条 guide: 基因组命中次数 + 坐标一致性 ===")
for (gene, s, pam, chrom, st), n in sorted(guides.items()):
    # 全基因组命中数(双链)
    hits_plus = sum(seq.count(s) for seq in genome.values())
    hits_minus = sum(seq.count(revcomp(s)) for seq in genome.values())
    total = hits_plus + hits_minus
    # 记录坐标处是否命中 & 是否 off-by-one
    g = genome[chrom]
    strand, pos = None, None
    i = g.find(s)
    if i>=0: strand, pos = "+", i+1
    else:
        j = g.find(revcomp(s))
        if j>=0: strand, pos = "-", j+1
    coord_ok = "✅" if pos==st else (f"⚠️off-by-{st-pos}" if pos and abs(st-pos)<=2 else f"❌记录{st} vs 实际{pos}")
    multi = f"多拷贝x{total}" if total>1 else "唯一"
    print(f"{gene:<11} {s} {pam:<3} {strand}链 {coord_ok:<14} {multi} (表内x{n})")
