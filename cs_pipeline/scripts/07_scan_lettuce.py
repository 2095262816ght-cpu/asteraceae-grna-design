"""07: 莴苣 T2T 基因组基因区 gRNA 扫描，骨架见 B2 节。

只扫基因区（启动子 TSS 上游 2000bp + 全部外显子），禁止全基因组暴力扫描。
正链找 NGG 取上游 20nt；负链找 CCN 取下游 20nt 后反向互补。
"""
import re

import pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta

GFF_COLS = ["chrom", "source", "feature", "start", "end", "score", "strand", "frame", "attr"]
gff = pd.read_csv("data/lettuce/lettuce_t2t.gff3", sep="\t", comment="#",
                  header=None, names=GFF_COLS, low_memory=False)
fasta = Fasta("data/lettuce/lettuce_t2t.fa", as_raw=True)

genes = gff[gff.feature == "gene"].copy()            # feature 命名以实际 GFF 为准，先核对再写死
genes["gene_id"] = genes.attr.str.extract(r"ID=([^;]+)")
exons = gff[gff.feature == "exon"].copy()
exons["gene_id"] = exons.attr.str.extract(r"Parent=([^;]+)")  # Parent 可能指向 mRNA，需按实际文件再映射


def regions_of(g):
    if g.strand == "+":
        prom = (g.chrom, max(g.start - 2000, 1), g.start, "+", "promoter")
    else:
        prom = (g.chrom, g.end, g.end + 2000, "-", "promoter")
    yield prom
    for _, e in exons[exons.gene_id == g.gene_id].iterrows():
        yield (e.chrom, e.start, e.end, g.strand, "exon")


PAM_FWD = re.compile(r"(?=([ACGT]GG))")
PAM_REV = re.compile(r"(?=(CC[ACGT]))")


def scan_region(chrom, start, end, strand, rtype, gene_id):
    seq = str(fasta[chrom][start - 1:end]).upper()   # pyfaidx 0-based 含端点
    out = []
    for m in PAM_FWD.finditer(seq):
        if m.start() >= 20:
            g20 = seq[m.start() - 20: m.start()]
            out.append((gene_id, chrom, start + m.start() - 20, start + m.start() + 2,
                        "+", g20, seq[m.start():m.start() + 3], rtype))
    for m in PAM_REV.finditer(seq):
        s = m.start() + 3
        if s + 20 <= len(seq):
            g20 = str(Seq(seq[s: s + 20]).reverse_complement())
            out.append((gene_id, chrom, start + m.start(), start + s + 19,
                        "-", g20, str(Seq(seq[m.start():m.start() + 3]).reverse_complement()), rtype))
    return out


rows = []
for _, g in genes.iterrows():
    for reg in regions_of(g):
        rows.extend(scan_region(*reg, g.gene_id))

cols = ["gene_id", "chrom", "start", "end", "strand", "seq20", "pam", "region_type"]
cand = pd.DataFrame(rows, columns=cols).drop_duplicates(["chrom", "start", "end", "strand"])


def get_seq30(r):
    # 与 01 脚本同一约定：+链取 [start-4, end+3]，-链取 [start-3, end+4] 再反向互补
    if r.strand == "+":
        return str(fasta[r.chrom][r.start - 5: r.end + 3]).upper()
    s = str(fasta[r.chrom][r.start - 4: r.end + 4]).upper()
    return str(Seq(s).reverse_complement())


cand["seq30"] = cand.apply(get_seq30, axis=1)
cand = cand[cand.seq30.str.fullmatch(r"[ACGT]{30}")]  # 边界截断的丢弃
cand.insert(0, "guide_id", [f"Lsat_{i:06d}" for i in range(len(cand))])
cand.to_csv("results/grna_candidates_lettuce_0923.csv", index=False)
print(f"OK: {len(cand)} candidates")
