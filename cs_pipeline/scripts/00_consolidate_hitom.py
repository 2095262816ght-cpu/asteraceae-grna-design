# -*- coding: utf-8 -*-
"""
00_consolidate_hitom.py
A0 / 9.9 任务收尾 —— 生物系 Hi-TOM 交付数据的机械清洗合并。

输入：data/raw/hitom_raw/ 下三份 GBK 编码 CSV（原始交付，留痕不入库）。
输出：data/hitom/hitom_clean_v1.csv（UTF-8），以及打印统计。

原则：只做机械清洗，不做任何生物学判断
（不删批次、不归一化 —— 那是生物系的口径）。
"""
import os
import re
import sys
import pandas as pd

RAW_DIR = os.path.join("data", "raw", "hitom_raw")
OUT_CSV = os.path.join("data", "hitom", "hitom_clean_v1.csv")
STATS_OUT = os.path.join("results", "consolidate_stats_0909.txt")

# 原始列名（含空格/中文） -> 接口约定列名
COLMAP = {
    "guide-id": "guide_id",
    "gene-id": "gene_id",
    "seq-20": "seq20",
    "pam": "pam",
    "chrom": "chrom",
    "start": "start",
    "end": "end",
    "strand": "strand",
    "batch": "batch",
    "rep": "rep",
    "indel_pct": "indel_pct",
    "efficiency-norm": "efficiency_norm",
    "备注": "note",
}

SEQ20_RE = re.compile(r"^[ACGT]{20}$")
PAM_RE = re.compile(r"^[ACGT]GG$")

stats_lines = []


def log(msg):
    print(msg)
    stats_lines.append(msg)


def main():
    frames = []
    for fn in sorted(os.listdir(RAW_DIR)):
        if not fn.lower().endswith(".csv"):
            continue
        path = os.path.join(RAW_DIR, fn)
        df = pd.read_csv(path, encoding="gbk", dtype=str)
        # 列名标准化：strip + 映射
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={k: v for k, v in COLMAP.items() if k in df.columns})
        df["source_file"] = fn
        log(f"读取 {fn}: {len(df)} 行")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    log(f"合并后总行数: {len(df)}")

    for col in ["efficiency_norm", "note"]:
        if col not in df.columns:
            df[col] = pd.NA

    # ---- 值清洗 ----
    df["guide_id"] = df["guide_id"].astype("string").str.strip()
    df["gene_id"] = df["gene_id"].astype("string").str.strip().str.upper()
    df["seq20"] = df["seq20"].astype("string").str.strip().str.upper()
    df["pam"] = df["pam"].astype("string").str.strip().str.upper()
    df["batch"] = df["batch"].astype("string").str.strip()
    df["chrom"] = df["chrom"].astype("string").str.strip()
    df["strand"] = df["strand"].astype("string").str.strip()

    # rep: 缺失 / "暂不填" -> 1
    rep = df["rep"].astype("string").str.strip()
    df["rep"] = rep.where(rep.notna() & (rep != "") & (rep != "暂不填"), "1")

    # start/end: 保留原样（多为"暂不填"），缺失置 NA
    for col in ["start", "end"]:
        v = df[col].astype("string").str.strip()
        df[col] = v.where(v.notna() & (v != ""), pd.NA)

    # indel_pct: 去 % 转 float
    ip = df["indel_pct"].astype("string").str.strip().str.rstrip("%")
    df["indel_pct"] = pd.to_numeric(ip, errors="coerce")
    n_bad_indel = int(df["indel_pct"].isna().sum())
    if n_bad_indel:
        log(f"警告: indel_pct 无法解析的行数: {n_bad_indel}")

    # ---- 行级剔除：seq20 / pam 不合法 ----
    bad_seq_mask = ~df["seq20"].fillna("").str.fullmatch(r"[ACGT]{20}")
    bad_pam_mask = ~df["pam"].fillna("").str.fullmatch(r"[ACGT]GG")
    drop_mask = bad_seq_mask | bad_pam_mask
    n_drop = int(drop_mask.sum())
    if n_drop:
        log(f"剔除 seq20 非 [ACGT]{{20}} 或 pam 非 NGG 的行: {n_drop}")
        examples = df.loc[drop_mask, ["source_file", "guide_id", "seq20", "pam"]].head(10)
        log("剔除示例（前 10 条）:\n" + examples.to_string(index=False))
    df = df.loc[~drop_mask].copy()

    # ---- guide_id 补全：空 -> TKSAUTO_{batch}_{四位序号} ----
    empty_mask = df["guide_id"].isna() | (df["guide_id"] == "")
    n_auto = int(empty_mask.sum())
    log(f"guide_id 为空的行数（补 TKSAUTO 前缀）: {n_auto}")
    counter = 0
    new_ids = []
    for idx, row in df.iterrows():
        if pd.isna(row["guide_id"]) or row["guide_id"] == "":
            counter += 1
            new_ids.append(f"TKSAUTO_{row['batch']}_{counter:04d}")
        else:
            new_ids.append(row["guide_id"])
    df["guide_id"] = new_ids

    # ---- 唯一键 uid = guide_id__batch ----
    df["uid"] = df["guide_id"] + "__" + df["batch"]
    n_dup_uid = int(df["uid"].duplicated().sum())
    log(f"uid (guide_id__batch) 重复行数（同 guide 同批多 rep，保留）: {n_dup_uid}")
    n_dup_guide = int(df["guide_id"].duplicated().sum())
    n_uniq_guide = int(df["guide_id"].nunique())
    log(f"guide_id 去重后数量: {n_uniq_guide}；跨批次/多 rep 重复出现的 guide 行数: {n_dup_guide}")

    out_cols = ["uid", "guide_id", "gene_id", "seq20", "pam", "chrom", "start",
                "end", "strand", "batch", "rep", "indel_pct",
                "efficiency_norm", "note", "source_file"]
    df = df[out_cols]
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    log(f"输出 {OUT_CSV}: {len(df)} 行")
    log("batch 分布:\n" + df["batch"].value_counts().to_string())

    os.makedirs("results", exist_ok=True)
    with open(STATS_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(stats_lines) + "\n")


if __name__ == "__main__":
    main()
