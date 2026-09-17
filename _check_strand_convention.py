import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import openpyxl

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

genome={}; cur=None
for line in open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta"):
    if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
    elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}

wb = openpyxl.load_workbook(r"cs_pipeline\data\1_Hi-results-12-20260913.xlsx", read_only=True)
ws = wb["Sheet1"]
rows = list(ws.iter_rows(values_only=True))
hdr = [str(c).strip() for c in rows[0]]
c = {h: i for i, h in enumerate(hdr)}

guides = {}
for r in rows[1:]:
    if not r or not r[c["guide-id"]]: continue
    s = str(r[c["seq-20"]]).strip().upper()
    if len(s)!=20 or set(s)-set("ACGT"): continue
    key = (str(r[c["gene-id"]]).replace("evm.model.",""), s, str(r[c["pam"]]).strip().upper(),
           str(r[c["chrom"]]).strip(), int(r[c["start"]]), int(r[c["end"]]))
    guides[key] = guides.get(key, 0) + 1

n_plus = n_minus = n_none = rows_plus = rows_minus = 0
print(f"{'gene':<12}{'seq20':<22}{'pam':<5}{'记录坐标':<26}基因组验证")
for (gene, s, pam, chrom, st, en), n in sorted(guides.items()):
    gseq = genome.get(chrom, "")
    i = gseq.find(s)
    j = gseq.find(revcomp(s))
    if i >= 0:
        down = gseq[i+20:i+23].upper()
        ok = "PAM吻合" if down==pam else f"下游实际={down}"
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(60) + f" 正链@{i+1} {ok}")
        n_plus += 1; rows_plus += n
    elif j >= 0:
        up = revcomp(gseq[j-3:j])
        ok = "PAM吻合" if up.upper()==pam else f"实际PAM={up}"
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(60) + f" 负链(正链坐标{j+1}) {ok}")
        n_minus += 1; rows_minus += n
    else:
        print(f"{gene:<12}{s:<22}{pam:<5}{chrom}:{st}-{en} (x{n})".ljust(60) + " 基因组中不存在")
        n_none += 1
print(f"\nguide: 正链 {n_plus} 条({rows_plus}行) / 负链 {n_minus} 条({rows_minus}行) / 未命中 {n_none} 条")
print(f"Sheet1 strand 列全部记为 '-' —— 按用户约定，正链 {rows_plus} 行记错")
