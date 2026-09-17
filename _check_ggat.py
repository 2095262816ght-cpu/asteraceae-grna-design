import pandas as pd, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

for p, tag in [
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY2198-USR-4411-Hi-TOM-sequencing-result_processed_fixed.xlsx", "SY2198_fixed"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\consolidation_sources\all-SY4070-USR-8145-Hi-TOM-sequencing_processed.xlsx", "SY4070(未改)"),
    (r"D:\lifesciencechallenge\cs_pipeline\data\raw\hitom\1_Hi-results-12-20260913_fixed.xlsx", "大表_fixed"),
]:
    xl = pd.ExcelFile(p)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        if "seq-20" not in df.columns:
            continue
        m = df[df["seq-20"].astype(str).str.strip().str.upper() == "GGATTGCTGCTGAGAAGGCC"]
        if len(m):
            print(f"=== {tag} [{sh}] GGATTGCTGCTGAGAAGGCC {len(m)}行 ===")
            cols = [c for c in [" guide-id", "guide-id", "gene-id", "pam", "chrom", "start ", "start", " end", "end", " strand", "strand", "batch", "备注"] if c in df.columns]
            print(m[cols].head(6).to_string())
