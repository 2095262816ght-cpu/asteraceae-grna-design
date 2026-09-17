import pandas as pd, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

for p, tag in [
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY2198-USR-4411-Hi-TOM-sequencing-result_processed.xlsx", "SY2198 processed(旧)"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY2198-USR-4411-Hi-TOM-sequencing-result_processed_fixed.xlsx", "SY2198 processed_fixed"),
]:
    xl = pd.ExcelFile(p)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        print("=" * 20, tag, sh, df.shape)
        print(list(df.columns))
        print(df.head(3).to_string())
        # 找 LG03.2345 / GGCGTT / TTATTTT 行
        for col in df.columns:
            s = df[col].astype(str)
            for pat in ["LG03.2345", "GGCGTTAGATTGACAGAAGA", "TTATTTTTCATGTTCTAATT", "LG02.6246", "LG01.6995"]:
                n = s.str.contains(pat).sum()
                if n:
                    print(f"  列[{col}] 含 {pat}: {n} 行")
