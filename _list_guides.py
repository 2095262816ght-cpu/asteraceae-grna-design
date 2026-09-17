import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

# 大表中全部 20bp guide（seq-20）去重
import pandas as pd
df = pd.ExcelFile(r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx").parse("Sheet1")
guides = {}
for _, r in df.iterrows():
    g = str(r["gene-id"]).replace("evm.model.", "")
    s = str(r["seq-20"]).strip().upper()
    chrom = str(r["chrom"]).strip()
    st = r["start "]; en = r[" end"]
    if re.fullmatch(r"[ACGT]{20}", s):
        guides.setdefault((g, s, chrom, st, en), 0)
        guides[(g, s, chrom, st, en)] += 1
print(f"大表共 {len(df)} 行，去重后 (gene,seq,chrom,start,end) 组合 {len(guides)} 组")
for k, v in sorted(guides.items()):
    print(k, f"x{v}")
