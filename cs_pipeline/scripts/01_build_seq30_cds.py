# -*- coding: utf-8 -*-
"""
01_build_seq30_cds.py
A0 / 9.9 —— 坐标缺失时通过 CDS 映射生成 30bp 上下文序列。

背景：生物系交付的 Hi-TOM 表没有基因组坐标（start/end 为"暂不填"），
因此本脚本不走坐标（已有的坐标版 01_build_seq30.py 不动），改为：
  在对应 gene_id 的 CDS 序列及其反向互补中搜索 seq20+pam（23nt），
  唯一命中后取 上游4nt + 23nt + 下游3nt = 30nt。

局限（写入统计文件）：
  - 命中位置若在外显子交界处，侧翼碱基是 CDS 上下文（转录本拼接后），
    而非基因组上下文（可能跨越内含子）。
  - 靠近 CDS 端点、侧翼不足的行被剔除（boundary 类）。

硬断言：每行 len(seq30)==30、仅含 ACGT、seq30[4:24]==seq20、seq30[24:27]==pam，
断言不过即报错退出。
"""
import os
import re
import sys
import pandas as pd

IN_CSV = os.path.join("data", "hitom_clean_v1.csv")
FASTA = os.path.join("data", "tks_cds.fasta")
OUT_CSV = os.path.join("data", "hitom_seq30_0909.csv")
UNMATCHED_OUT = os.path.join("results", "seq30_unmatched_0909.csv")

_RC = str.maketrans("ACGTacgt", "TGCAtgca")


def revcomp(s):
    return s.translate(_RC)[::-1]


def load_cds(path):
    cds = {}
    name = None
    parts = []
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
    """在 CDS 正反链合计搜索 target23（regex 前瞻匹配，允许重叠）。
    返回 (strand, offset_in_fwd_cds_of_match_start) 或状态字符串。"""
    hits = []  # (strand, start_pos_on_that_strand_seq)
    for strand, seq in (("+", cds_seq), ("-", revcomp(cds_seq))):
        for m in re.finditer(f"(?={re.escape(target23)})", seq):
            hits.append((strand, m.start()))
    if len(hits) == 0:
        return ("no_hit", None, None)
    if len(hits) > 1:
        return ("multi_hit", None, None)
    strand, pos = hits[0]
    seq_used = cds_seq if strand == "+" else revcomp(cds_seq)
    # offset 统一报告为正链 CDS 坐标（0-based）：- 链换算回正链
    if strand == "+":
        fwd_offset = pos
    else:
        fwd_offset = len(cds_seq) - (pos + len(target23))
    return ("ok", strand, seq_used, pos, fwd_offset)


def main():
    df = pd.read_csv(IN_CSV, dtype=str)
    df["indel_pct"] = pd.to_numeric(df["indel_pct"], errors="coerce")
    cds = load_cds(FASTA)
    print(f"clean 表 {len(df)} 行；CDS 条目 {len(cds)}")

    counts = {"ok": 0, "no_gene": 0, "no_hit": 0, "multi_hit": 0, "boundary": 0}
    unmatched_rows = []
    out_rows = []

    for _, row in df.iterrows():
        gene = row["gene_id"]
        target = row["seq20"] + row["pam"]
        rec = row.to_dict()
        if gene not in cds:
            counts["no_gene"] += 1
            rec["drop_reason"] = "gene_not_in_cds"
            unmatched_rows.append(rec)
            continue
        res = find_unique(cds[gene], target)
        status = res[0]
        if status != "ok":
            counts[status] += 1
            rec["drop_reason"] = status
            unmatched_rows.append(rec)
            continue
        _, strand, seq_used, pos, fwd_offset = res
        lo, hi = pos - 4, pos + 23 + 3
        if lo < 0 or hi > len(seq_used):
            counts["boundary"] += 1
            rec["drop_reason"] = "boundary"
            unmatched_rows.append(rec)
            continue
        seq30 = seq_used[lo:hi]
        rec["seq30"] = seq30
        rec["cds_strand"] = strand
        rec["cds_offset"] = fwd_offset
        counts["ok"] += 1
        out_rows.append(rec)

    out = pd.DataFrame(out_rows)

    # ---- 硬断言 ----
    assert len(out) > 0, "没有任何行成功映射"
    assert (out["seq30"].str.len() == 30).all(), "存在 seq30 长度 != 30"
    assert out["seq30"].str.fullmatch(r"[ACGT]{30}").all(), "存在 seq30 含非 ACGT 字符"
    assert (out["seq30"].str[4:24] == out["seq20"]).all(), "seq30[4:24] != seq20"
    assert (out["seq30"].str[24:27] == out["pam"]).all(), "seq30[24:27] != pam"

    out.to_csv(OUT_CSV, index=False, encoding="utf-8")
    pd.DataFrame(unmatched_rows).to_csv(UNMATCHED_OUT, index=False, encoding="utf-8")

    print("---- 映射统计 ----")
    for k, v in counts.items():
        print(f"{k}: {v}")
    print(f"输出 {OUT_CSV}: {len(out)} 行；未匹配清单 {UNMATCHED_OUT}: {len(unmatched_rows)} 行")
    print("断言全部通过")


if __name__ == "__main__":
    main()
