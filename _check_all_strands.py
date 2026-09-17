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
           str(r["chrom"]).strip(), int(r["start"]), int(r["end"]))
    guides.setdefault(key, 0)
    guides[key] += 1

print(f"{'gene':<12}{'seq20':<22}{'pam':<5}{'记录坐标':<24}{'基因组验证'}")
for (gene, s, pam, chrom, st, en), n in sorted(guides.items()):
    gseq = genome.get(chrom, "")
    i = gseq.find(s)          # 正链直接命中
    j = gseq.find(revcomp(s)) # 负链命中(revcomp 落在正链)
    if i >= 0:
        down = gseq[i+20:i+23]
        ok = "✅PAM吻合" if down.upper()==pam else f"⚠️下游实际={down}"
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(58) + f" 正链@{i+1} {ok}")
    elif j >= 0:
        up = revcomp(gseq[j-3:j])
        ok = "✅PAM吻合" if up.upper()==pam else f"⚠️实际PAM={up}"
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(58) + f" 负链(正链坐标{j+1}) {ok}")
    else:
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(58) + " ❌基因组中不存在")
