import pandas as pd, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

p = r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY2198-USR-4411-Hi-TOM-sequencing-result_processed_fixed.xlsx"
df = pd.ExcelFile(p).parse("Sheet1")

# 1) 被改过的行（有备注的）
print("=== 有备注的行 ===")
noted = df[df["备注"].notna()]
print(noted[["guide-id", "gene-id", "seq-20", "pam", "chrom", "indel_pct", "备注"]].to_string())

# 2) 剩下 10 行 LG03.2345 在 USR-4411 中的位置
print("\n=== 剩余 LG03.2345 行 ===")
sub = df[df["gene-id"].astype(str).str.contains("LG03.2345")]
print(sub[["guide-id", "gene-id", "seq-20", "pam", "indel_pct"]].to_string())

# 3) LG01.6995 的 3 行
print("\n=== LG01.6995 行 ===")
sub2 = df[df["gene-id"].astype(str).str.contains("LG01.6995")]
print(sub2[["guide-id", "gene-id", "seq-20", "pam", "chrom", "备注"]].to_string())
