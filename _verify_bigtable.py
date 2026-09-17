import pandas as pd, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

for p, tag in [
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx", "hitom/_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\1_Hi-results-12-20260913.xlsx", "data/1_Hi-results-12-20260913"),
]:
    xl = pd.ExcelFile(p)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        print("=" * 20, tag, sh, df.shape)
        print(list(df.columns))
        print(df.head(3).to_string())
        # residual fake genes check
        if "gene-id" in df.columns:
            g = df["gene-id"].astype(str)
            for fake in ["LG02.3008", "LG07.262", "LG02.6246", "LG03.2345"]:
                n = g.str.contains(fake).sum()
                if n:
                    print(f"!! 残留 {fake}: {n} 行")
        for col in df.columns:
            if df[col].astype(str).str.contains("TTCAAGTTCTAAGTAATCCT|LG02\\.3008|LG07\\.262|LG02\\.6246").any():
                print(f"!! 列 {col} 含可疑值")
