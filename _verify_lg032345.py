import pandas as pd, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

for p, tag in [
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx", "hitom/_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\1_Hi-results-12-20260913.xlsx", "data/主表"),
]:
    df = pd.ExcelFile(p).parse("Sheet1")
    print("=" * 25, tag)
    sub = df[df["gene-id"].astype(str).str.contains("LG03.2345")]
    print(sub[[" guide-id", "gene-id", "seq-20", "pam", "chrom", "start ", " end", "batch", "备注"]].to_string())
    print("--- 含 TTCAAG / LG02.3008 / LG07.262 / LG02.6246 的行 ---")
    for pat in ["TTCAAGTTCTAAGTAATCCT", "LG02.3008", "LG07.262", "LG02.6246"]:
        m = df[df["seq-20"].astype(str).str.contains(pat) | df["gene-id"].astype(str).str.contains(pat)]
        print(pat, "->", len(m), "行")
        if len(m) and pat != "TTCAAGTTCTAAGTAATCCT":
            print(m[[" guide-id", "gene-id", "seq-20", "备注"]].head(5).to_string())
