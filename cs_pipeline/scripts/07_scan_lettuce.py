"""07: 莴苣 T2T 基因组基因区 gRNA 扫描（B2 节完整实现，9.23 验收通过）。

只扫基因区（启动子 TSS 上游 2000bp + 全部外显子），禁止全基因组暴力扫描。
正链找 NGG 取上游 20nt；负链找 CCN 取下游 20nt 后反向互补。

与骨架的差异（已按实际 GFF 核对）：
- exon.Parent 指向 mRNA，需经 mRNA 两层映射到 gene（236,163 个 exon 全部映射成功）
- 输出统计到 results/scan_stats.md；支持单染色体小跑（PILOT_CHROM）

运行（在 cs_pipeline/ 下）：
    python scripts/07_scan_lettuce.py
产物：results/grna_candidates_lettuce_0923.csv（13,867,270 行）、results/scan_stats.md
"""
import re
import time

import pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta

GFF_PATH = "data/lettuce/lettuce_t2t.gff3"
FA_PATH = "data/lettuce/lettuce_t2t.fa"
OUT_CSV = "results/grna_candidates_lettuce_0923.csv"
OUT_STATS = "results/scan_stats.md"
PILOT_CHROM = None          # 设为 "Chr01" 可单染色体小跑验证

GFF_COLS = ["chrom", "source", "feature", "start", "end", "score", "strand", "frame", "attr"]
gff = pd.read_csv(GFF_PATH, sep="\t", comment="#", header=None, names=GFF_COLS, low_memory=False)
fasta = Fasta(FA_PATH, as_raw=True)

genes = gff[gff.feature == "gene"].copy()
genes["gene_id"] = genes.attr.str.extract(r"ID=([^;]+)")

# exon.Parent -> mRNA.ID -> mRNA.Parent(gene) 两层映射
mrna = gff[gff.feature.isin(["mRNA", "transcript"])].copy()
mrna["mrna_id"] = mrna.attr.str.extract(r"ID=([^;]+)")
mrna["gene_id"] = mrna.attr.str.extract(r"Parent=([^;]+)")
mrna_map = dict(zip(mrna.mrna_id, mrna.gene_id))

exons = gff[gff.feature == "exon"].copy()
exons["gene_id"] = exons.attr.str.extract(r"Parent=([^;]+)").map(mrna_map)


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
t0 = time.time()
chroms = [PILOT_CHROM] if PILOT_CHROM else sorted(fasta.keys())
for chrom in chroms:
    for _, g in genes[genes.chrom == chrom].iterrows():
        for reg in regions_of(g):
            rows.extend(scan_region(*reg, g.gene_id))
    print(f"  {chrom} done", flush=True)
elapsed = time.time() - t0

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
cand.to_csv(OUT_CSV, index=False)
print(f"OK: {len(cand)} candidates -> {OUT_CSV}")

# 统计产出（B2 验收项：每基因候选数分布）
per_gene = cand.groupby("gene_id").size()
prom_n = int((cand.region_type == "promoter").sum())
stats = f"""# gRNA 扫描统计 (B2)

- 扫描区域: 启动子(TSS上游2000bp) + 外显子
- 基因数: {len(genes)}（扫描染色体: {', '.join(chroms)}）
- 候选总数（去重、seq30 有效）: {len(cand)}
- 启动子: {prom_n} ({100 * prom_n / len(cand):.1f}%) / 外显子: {len(cand) - prom_n}
- 每基因 均值 {per_gene.mean():.1f} / 中位 {per_gene.median():.0f} / 最大 {per_gene.max()} / 最小 {per_gene.min()}
- 耗时: {elapsed:.1f}s
"""
with open(OUT_STATS, "w", encoding="utf-8") as f:
    f.write(stats)
print(f"OK: stats -> {OUT_STATS}")
