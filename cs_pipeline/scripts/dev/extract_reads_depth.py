# -*- coding: utf-8 -*-
"""extract_reads_depth.py — 从原始 Hi-TOM xls 文件中逐块提取测序深度与编辑 reads 数

输入:
  - 7 个旧批次原始交付文件 (491 块)
  - NEWdata 18 个新批次结果文件 (877 块)
输出:
  - data/hitom/hitom_reads_depth_0921.csv (1368 行，字段: guide_id, batch, block, total_reads, wt_reads, non_wt_reads)
"""
import glob
import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loader import load_hitom, split_blocks

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_CSV = "data/hitom/hitom_reads_depth_0921.csv"

# 1. 旧主表 7 批次文件 (依 1_Hi-results-12-20260913.xlsx 出现顺序)
OLD_FILES = [
    ("USR-5713", "data/raw/hitom/R1_sequencing/2022-01-30/USR-5713/1_result/all-SY2793-USR-5713-Hi-TOM-sequencing-result.xls"),
    ("USR-5712", "data/raw/hitom/R1_sequencing/2022-01-30/USR-5712/1_result/all-SY2795-USR-5712-Hi-TOM-sequencing-result.xls"),
    ("USR-23709", "data/raw/consolidation_sources/all-SY12100-USR-23709-Hi-TOM-sequencing-result_original.xls"),
    ("USR-25902", "data/raw/consolidation_sources/all-SY13249-USR-25902-Hi-TOM-sequencing-result_original.xls"),
    ("USR-4411", "data/raw/hitom/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls"),
    ("USR-8145", "data/raw/hitom/all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls"),
    ("USR-26162", "data/raw/consolidation_sources/merged_T1T2_all-SY13345-USR-26162-Hi-TOM-sequencing-result_original.xls"),
]


def parse_block_reads(b):
    """解析单个 block 的 reads 统计"""
    total = 0.0
    wt = 0.0
    non_wt = 0.0
    for v in b["vars"]:
        try:
            rn = float(v["Reads number"])
        except Exception:
            continue
        if pd.isna(rn) or rn <= 0:
            continue
        total += rn
        is_wt = (str(v["Left variation type"]) == "WT") and (str(v["Right variation type"]) == "WT")
        if is_wt:
            wt += rn
        else:
            non_wt += rn
    return total, wt, non_wt


def main():
    rows = []
    tks_idx = 0

    print("=== 解析旧批次 491 块 ===")
    for b_name, fpath in OLD_FILES:
        assert os.path.exists(fpath), f"文件不存在: {fpath}"
        blocks = split_blocks(load_hitom(fpath))
        print(f"  {b_name}: {len(blocks)} 块 ({fpath})")
        for b in blocks:
            tks_idx += 1
            gid = f"TKS_{tks_idx:04d}"
            tot, wt, non_wt = parse_block_reads(b)
            rows.append({
                "guide_id": gid,
                "batch": b_name,
                "block": b["block"],
                "total_reads": tot,
                "wt_reads": wt,
                "non_wt_reads": non_wt,
                "source_file": os.path.basename(fpath)
            })

    print(f"旧批次已提取 {len(rows)} 行 (期望 491)")
    assert len(rows) == 491

    print("\n=== 解析 NEWdata 18 个结果文件 (877 块) ===")
    new_files = sorted(glob.glob("data/raw/hitom/NEWdata_0918/02_HiTOM*/*/*.xls"))
    assert len(new_files) == 18, f"期望 18 个新批次文件，找到 {len(new_files)}"
    for fpath in new_files:
        m = re.search(r"USR-(\d+)", fpath)
        batch = "USR-" + m.group(1) if m else "UNKNOWN"
        blocks = split_blocks(load_hitom(fpath))
        print(f"  {batch}: {len(blocks)} 块 ({os.path.basename(fpath)})")
        for b in blocks:
            tks_idx += 1
            gid = f"TKS_{tks_idx:04d}"
            tot, wt, non_wt = parse_block_reads(b)
            rows.append({
                "guide_id": gid,
                "batch": batch,
                "block": b["block"],
                "total_reads": tot,
                "wt_reads": wt,
                "non_wt_reads": non_wt,
                "source_file": os.path.basename(fpath)
            })

    print(f"\n总计提取 {len(rows)} 行 (期望 1368)")
    assert len(rows) == 1368

    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df_out.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"已成功写入 {OUT_CSV}")

    # 验证与 base/train969 的匹配率
    base = pd.read_csv("data/hitom/hitom_seq30_merged_0918.csv")
    merged = base.merge(df_out[["guide_id", "total_reads", "non_wt_reads"]], on="guide_id", how="left")
    print(f"与 base (1361行) 匹配成功: {merged['total_reads'].notna().sum()} / {len(base)}")
    assert merged["total_reads"].notna().all(), "存在未能匹配深度的 guide_id!"


if __name__ == "__main__":
    main()
