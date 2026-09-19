# -*- coding: utf-8 -*-
"""
10_rebuild_full_dataset.py
2026-09-16 全量重跑 —— 以改正版 xlsx 为唯一事实源，重建 clean 表 + seq30。

与 00/01 的差异：
  - 输入由 data/raw/hitom_raw/ 三份旧交付 CSV 改为 data/1_Hi-results-12-20260913.xlsx
    （含 9.15/9.16 全部更正：5712 序列、6995/6999 窗口、strand、坐标、PAM、5712 indel 写回）；
  - efficiency_norm 按训练集实证约定 = indel_pct × 100（scores_merged_0911 中 260/260
    行 efficiency_norm 与 indel_pct(%) 逐值相等）；
  - 过滤规则与 00 相同：seq20 须 ^[ACGT]{20}$、pam 须 ^[ACGT]GG$（剔除非 NGG 的 4 行 ACT）；
  - 映射逻辑与 01_build_seq30_cds.py 相同（CDS 双链搜索 23nt，唯一命中取 30nt）。

输出：
  data/hitom/hitom_clean_merged_0918.csv
  data/hitom/hitom_seq30_merged_0918.csv
  results/seq30_unmatched_merged_0918.csv

与 01 的另一差异：CDS 未命中的行（靶点在内含子/基因间区，如 USR-5712 的 GAAA guide）
回退到坐标版逻辑（01_build_seq30.py）——按表内 start/end/strand 从基因组取
上游4+guide20+PAM3+下游3，自校验 seq30[4:24]==seq20、seq30[24:27]==pam。
"""
import os
import re
import pandas as pd

XLSX = os.path.join("data", "1_Hi-results-13-merged-20260918.xlsx")
FASTA = os.path.join("data", "raw", "screening_tools", "TKS_cds.fasta")
GENOME = os.path.join("data", "reference_genomes", "2-1_TKS.genome.fasta")
CLEAN_OUT = os.path.join("data", "hitom", "hitom_clean_merged_0918.csv")
SEQ30_OUT = os.path.join("data", "hitom", "hitom_seq30_merged_0918.csv")
UNMATCHED_OUT = os.path.join("results", "seq30_unmatched_merged_0918.csv")

COLMAP = {
    "guide-id": "guide_id", "gene-id": "gene_id", "seq-20": "seq20", "pam": "pam",
    "chrom": "chrom", "start": "start", "end": "end", "strand": "strand",
    "batch": "batch", "rep": "rep", "indel_pct": "indel_pct",
    "efficiency-norm": "efficiency_norm_src", "备注": "note",
}

_RC = str.maketrans("ACGTacgt", "TGCAtgca")


def revcomp(s):
    return s.translate(_RC)[::-1]


def load_cds(path):
    cds, name, parts = {}, None, []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    cds[name] = "".join(parts).upper()
                name = line[1:].split()[0].strip().upper()
                parts = []
            else:
                parts.append(line)
    if name is not None:
        cds[name] = "".join(parts).upper()
    return cds


def find_unique(cds_seq, target23):
    hits = []
    for strand, seq in (("+", cds_seq), ("-", revcomp(cds_seq))):
        for m in re.finditer(f"(?={re.escape(target23)})", seq):
            hits.append((strand, m.start()))
    if len(hits) == 0:
        return ("no_hit", None, None, None, None)
    if len(hits) > 1:
        return ("multi_hit", None, None, None, None)
    strand, pos = hits[0]
    seq_used = cds_seq if strand == "+" else revcomp(cds_seq)
    fwd_offset = pos if strand == "+" else len(cds_seq) - (pos + len(target23))
    return ("ok", strand, seq_used, pos, fwd_offset)


def load_genome(path):
    genome, name, parts = {}, None, []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if name is not None:
                    genome[name] = "".join(parts).upper()
                name = line[1:].split()[0].strip()
                parts = []
            elif name is not None:
                parts.append(line.upper())
    if name is not None:
        genome[name] = "".join(parts).upper()
    return genome


def seq30_from_genome(genome, chrom, start, end, strand):
    """按表内坐标约定（1-based，end=start+20，覆盖 guide 20nt）取基因组上下文 seq30。
    +链：[start-4, start+20+PAM3+下游3]； -链：取正链 [start-6, start+23] 后反向互补。
    坐标/链向任何不一致都会在调用处的自校验断言中暴露。"""
    g = genome[chrom]
    s = int(start)
    if strand == "+":
        return g[s - 5: s + 25]
    return revcomp(g[s - 7: s + 23])


def main():
    # ---- 00 等价：读取 + 清洗 + 过滤 ----
    df = pd.read_excel(XLSX, sheet_name="Sheet1", dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in COLMAP.items() if k in df.columns})
    df["source_file"] = os.path.basename(XLSX)

    df["guide_id"] = df["guide_id"].astype("string").str.strip()
    df["gene_id"] = df["gene_id"].astype("string").str.strip().str.upper()
    df["seq20"] = df["seq20"].astype("string").str.strip().str.upper()
    df["pam"] = df["pam"].astype("string").str.strip().str.upper()
    df["batch"] = df["batch"].astype("string").str.strip()
    df["chrom"] = df["chrom"].astype("string").str.strip()
    df["strand"] = df["strand"].astype("string").str.strip()
    rep = df["rep"].astype("string").str.strip()
    df["rep"] = rep.where(rep.notna() & (rep != "") & (rep != "暂不填"), "1")
    for col in ["start", "end"]:
        v = df[col].astype("string").str.strip()
        df[col] = v.where(v.notna() & (v != ""), pd.NA)
    df["note"] = df["note"].astype("string").fillna("")
    df["indel_pct"] = pd.to_numeric(df["indel_pct"], errors="coerce")
    assert df["indel_pct"].notna().all(), "存在无法解析的 indel_pct"

    bad = ~(df["seq20"].str.fullmatch(r"[ACGT]{20}") & df["pam"].str.fullmatch(r"[ACGT]GG"))
    print(f"剔除非 NGG/非法序列: {bad.sum()} 行 ->",
          df.loc[bad, "guide_id"].tolist())
    df = df.loc[~bad].copy()

    # 标签约定：efficiency_norm = indel_pct(%)（与 scores_merged_0911 实证一致）
    assert (df["indel_pct"] <= 1).all(), "xlsx indel_pct 应为 0-1 小数"
    df["efficiency_norm"] = df["indel_pct"] * 100

    df["uid"] = df["guide_id"] + "__" + df["batch"]
    assert not df["uid"].duplicated().any(), "uid 重复"
    out_cols = ["uid", "guide_id", "gene_id", "seq20", "pam", "chrom", "start",
                "end", "strand", "batch", "rep", "indel_pct",
                "efficiency_norm", "note", "source_file"]
    df = df[out_cols]
    df.to_csv(CLEAN_OUT, index=False, encoding="utf-8")
    print(f"输出 {CLEAN_OUT}: {len(df)} 行")
    print("batch 分布:\n" + df["batch"].value_counts().to_string())

    # ---- 01 等价：CDS 双链映射 seq30；未命中回退基因组坐标版 ----
    cds = load_cds(FASTA)
    genome = load_genome(GENOME)
    print(f"\nCDS 条目 {len(cds)}；基因组染色体 {len(genome)}")
    counts = {"ok_cds": 0, "ok_genome": 0, "no_gene": 0, "no_hit": 0, "multi_hit": 0, "boundary": 0}
    unmatched_rows, out_rows = [], []
    for _, row in df.iterrows():
        gene, target = row["gene_id"], row["seq20"] + row["pam"]
        rec = row.to_dict()
        if gene not in cds:
            counts["no_gene"] += 1
            rec["drop_reason"] = "gene_not_in_cds"
            unmatched_rows.append(rec)
            continue
        status, strand, seq_used, pos, fwd_offset = find_unique(cds[gene], target)
        if status == "ok":
            lo, hi = pos - 4, pos + 23 + 3
            if lo < 0 or hi > len(seq_used):
                counts["boundary"] += 1
                rec["drop_reason"] = "boundary"
                unmatched_rows.append(rec)
                continue
            rec["seq30"] = seq_used[lo:hi]
            rec["cds_strand"] = strand
            rec["cds_offset"] = fwd_offset
            rec["seq30_source"] = "cds"
            counts["ok_cds"] += 1
            out_rows.append(rec)
            continue
        if status == "multi_hit":
            counts["multi_hit"] += 1
            rec["drop_reason"] = status
            unmatched_rows.append(rec)
            continue
        # CDS no_hit：回退基因组坐标版（靶点在 CDS 外，如内含子）
        try:
            seq30 = seq30_from_genome(genome, row["chrom"], row["start"], row["end"], row["strand"])
        except Exception:
            counts["no_hit"] += 1
            rec["drop_reason"] = "no_hit"
            unmatched_rows.append(rec)
            continue
        if len(seq30) != 30 or seq30[4:24] != row["seq20"] or seq30[24:27] != row["pam"]:
            counts["no_hit"] += 1
            rec["drop_reason"] = "no_hit_genome_mismatch"
            unmatched_rows.append(rec)
            continue
        rec["seq30"] = seq30
        rec["cds_strand"] = row["strand"]
        rec["cds_offset"] = pd.NA
        rec["seq30_source"] = "genome"
        counts["ok_genome"] += 1
        out_rows.append(rec)

    out = pd.DataFrame(out_rows)
    assert len(out) > 0
    assert (out["seq30"].str.len() == 30).all()
    assert out["seq30"].str.fullmatch(r"[ACGT]{30}").all()
    assert (out["seq30"].str[4:24] == out["seq20"]).all()
    assert (out["seq30"].str[24:27] == out["pam"]).all()

    out.to_csv(SEQ30_OUT, index=False, encoding="utf-8")
    pd.DataFrame(unmatched_rows).to_csv(UNMATCHED_OUT, index=False, encoding="utf-8")
    print("---- 映射统计 ----")
    for k, v in counts.items():
        print(f"{k}: {v}")
    print(f"输出 {SEQ30_OUT}: {len(out)} 行；未匹配 {UNMATCHED_OUT}: {len(unmatched_rows)} 行")
    if unmatched_rows:
        print(pd.DataFrame(unmatched_rows).groupby(["drop_reason", "gene_id"]).size().to_string())
    print("断言全部通过")


if __name__ == "__main__":
    main()
