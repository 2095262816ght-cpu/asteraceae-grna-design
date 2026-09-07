"""01: 从基因组坐标为 hitom_clean_v1.csv 补 30bp 上下文，产出 hitom_seq30_0909.csv。

seq30 = 4nt上游 + 20nt guide + 3nt PAM + 3nt下游（沿 guide 5'→3' 方向）。
start/end 为 1-based 闭区间，覆盖 seq20+PAM 共 23nt。
骨架见《分工详案_计算机系.md》A0 节。
"""
import pandas as pd
from Bio import SeqIO

genome = SeqIO.to_dict(SeqIO.parse("data/rubber_dandelion_ref.fa", "fasta"))
df = pd.read_csv("data/hitom_clean_v1.csv")


def get_seq30(row):
    # +链：取基因组 [start-4, end+3]（1-based），即切片 [start-5 : end+3]
    # -链：取 [start-3, end+4]，即切片 [start-4 : end+4]，再反向互补
    chrom = genome[row.chrom]
    if row.strand == "+":
        s = chrom.seq[row.start - 5: row.end + 3]
    else:
        s = chrom.seq[row.start - 4: row.end + 4].reverse_complement()
    return str(s).upper()


df["seq30"] = df.apply(get_seq30, axis=1)
assert df.seq30.str.len().eq(30).all() and df.seq30.str.fullmatch(r"[ACGT]{30}").all()
# 自校验：seq30 第 5-24 位必须等于 seq20，第 25-27 位必须等于 pam（防坐标取向反了）
assert (df.seq30.str[4:24] == df.seq20).all() and (df.seq30.str[24:27] == df.pam).all()
df.to_csv("data/hitom_seq30_0909.csv", index=False)
print(f"OK: {len(df)} rows -> data/hitom_seq30_0909.csv")
