"""Spike: T2T -> v1.1c liftover 可行性（完整版方案5 的前置判定）。两阶段：

  python spike_liftover.py extract          # 抽 T2T Chr1 / v1.1c Chr01 到 _scratch
  （在 WSL 中跑 minimap2 -x asm5 生成 spike.paf）
  python spike_liftover.py parse spike.paf  # 计算四条预注册判据并给出立项结论

预注册判据（跑前定死）：
  1. 查询覆盖率 >= 90%  （T2T Chr1 被 primary 比对块覆盖的比例）
  2. 比对一致性 >= 95%  （sum(nmatch)/sum(alnlen)）
  3. 共线性比例 >= 90%  （primary 块按 q 排序后链一致且 t 单调的相邻对占比）
  4. 地面真值   >= 80%  （<=20 条 Chr01 guide 的 T2T 精确坐标经 PAF 块 liftover 后落在
                        其 crosswalk LSA 基因启动子感知区间 ±10kb 内）
四条全过 => liftover 可信，完整版方案5 立项；任一不过 => 维持轻量版。

仅 stdlib。
"""
import csv
import sys
from pathlib import Path

BASE = Path("D:/lifesciencechallenge/cs_pipeline")
TMP = Path("D:/lifesciencechallenge/_scratch")
T2T_FA = BASE / "data/reference_genomes/3-1_LsT2T.genome.fa"
V11C_FA = BASE / "data/reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa"
V11C_GFF = BASE / "data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff"
XWALK = BASE / "results/crosswalk_lsa_t2t_0923.csv"
GUIDES = BASE / "demo/app_data.csv"

Q_CHROM, R_CHROM = "Chr1", "Chr01"


def log(m):
    print(m, flush=True)


def extract_chrom(fa_path, chrom, out_path):
    with open(fa_path, encoding="utf-8") as fh, open(out_path, "w", encoding="utf-8") as fo:
        writing = False
        for line in fh:
            if line.startswith(">"):
                writing = line[1:].split()[0] == chrom
                if writing:
                    fo.write(f">{chrom}\n")
                continue
            if writing:
                fo.write(line)
    log(f"  extracted {chrom} -> {out_path.name} ({out_path.stat().st_size / 1e6:.0f} MB)")


FRAG = 5_000_000
OVERLAP = 20_000


def fragment_query():
    seq = "".join(l.strip() for l in open(TMP / "spike_t2t_Chr1.fa") if not l.startswith(">"))
    out = TMP / "spike_t2t_Chr1_frag.fa"
    with open(out, "w", encoding="utf-8") as fo:
        for i, s0 in enumerate(range(0, len(seq), FRAG)):
            fo.write(f">frag_{i:04d}_{s0}\n")
            for j in range(s0, min(s0 + FRAG + OVERLAP, len(seq)), 80):
                fo.write(seq[j:j + 80] + "\n")
    log(f"  fragmented -> {out.name} ({(len(seq) + FRAG - 1) // FRAG} records)")


def rc(s):
    return s.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


def parse_paf(path):
    hits = []
    for line in open(path, encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 12:
            continue
        tags = f[12:]
        tp = [t[5:] for t in tags if t.startswith("tp:A:")]
        primary = (tp[0] == "P") if tp else True
        hits.append({
            "qname": f[0], "q_st": int(f[2]), "q_en": int(f[3]),
            "strand": 1 if f[4] == "+" else -1,
            "t_st": int(f[7]), "t_en": int(f[8]),
            "nmatch": int(f[9]), "blen": int(f[10]), "mapq": int(f[11]),
            "primary": primary,
        })
    return hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "frag":
        fragment_query()
        return
    if sys.argv[1] == "extract":
        log("[1] 抽取染色体 …")
        extract_chrom(V11C_FA, R_CHROM, TMP / "spike_v11c_Chr01.fa")
        extract_chrom(T2T_FA, Q_CHROM, TMP / "spike_t2t_Chr1.fa")
        log("下一步在 WSL 中运行：")
        log("  minimap2 -x asm5 -t 4 spike_v11c_Chr01.fa spike_t2t_Chr1.fa > spike.paf 2> spike_mm2.err")
        return

    paf = Path(sys.argv[2])
    qseq = "".join(l.strip() for l in open(TMP / "spike_t2t_Chr1.fa") if not l.startswith(">"))
    log(f"[2] 读 PAF {paf.name}；query len = {len(qseq):,}")
    import re
    hits = parse_paf(paf)
    for h in hits:  # 片段坐标 -> 全染色体坐标
        m = re.match(r"frag_\d+_(\d+)", h.get("qname", ""))
        off = int(m.group(1)) if m else 0
        h["q_st"] += off
        h["q_en"] += off
    prim = [h for h in hits if h["primary"]] or hits
    log(f"  比对块 {len(hits)}（primary {len(prim)}）")

    iv = sorted((h["q_st"], h["q_en"]) for h in prim)
    cov = ce = 0
    for s, e in iv:
        cov += e - s if s > ce else max(0, e - ce)
        ce = max(ce, e)
    coverage = 100.0 * cov / len(qseq)

    blen = sum(h["blen"] for h in prim)
    mlen = sum(h["nmatch"] for h in prim)
    identity = 100.0 * mlen / blen if blen else 0.0

    prim_s = sorted(prim, key=lambda h: h["q_st"])
    good = tot = 0
    for x, y in zip(prim_s, prim_s[1:]):
        tot += 1
        mono = (y["t_st"] >= x["t_st"]) if x["strand"] == 1 else (y["t_st"] <= x["t_st"])
        if x["strand"] == y["strand"] and mono:
            good += 1
    colinear = 100.0 * good / tot if tot else 0.0
    log(f"[3] 覆盖率 {coverage:.1f}% | 一致性 {identity:.1f}% | 共线性 {colinear:.1f}%")

    log("[4] 地面真值检查 …")
    lsa_of = {r["gene_id"]: r["lsa_primary"] for r in csv.DictReader(open(XWALK, encoding="utf-8"))}
    intervals = {}
    for line in open(V11C_GFF, encoding="utf-8"):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 9 or f[2] != "gene" or f[0] != R_CHROM:
            continue
        tag = [x for x in f[8].split(";") if x.startswith("ID=")]
        if not tag:
            continue
        s, e, st = int(f[3]), int(f[4]), f[6]
        es, ee = (s - 2000, e) if st == "+" else (s, e + 2000)
        intervals[tag[0][3:].replace(":gene", "")] = (max(es, 1), ee)
    guides = []
    for r in csv.DictReader(open(GUIDES, encoding="utf-8")):
        if r["chrom"] == "Chr01" and lsa_of.get(r["gene_id"]) in intervals:
            guides.append(r)
        if len(guides) >= 20:
            break
    ok = tested = 0
    for r in guides:
        s20 = r["seq20"].upper()
        p = qseq.find(s20)
        strand_q = "+"
        if p < 0:
            p, strand_q = qseq.find(rc(s20)), "-"
        if p < 0:
            continue
        tested += 1
        hit = next((h for h in prim_s if h["q_st"] <= p < h["q_en"]), None)
        if not hit:
            continue
        t = hit["t_st"] + (p - hit["q_st"]) if hit["strand"] == 1 else hit["t_en"] - (p - hit["q_st"])
        es, ee = intervals[lsa_of[r["gene_id"]]]
        if es - 10000 <= t <= ee + 10000:
            ok += 1
    truth = 100.0 * ok / tested if tested else 0.0
    log(f"  guide 真值 {ok}/{tested} = {truth:.1f}%")

    log("")
    checks = [("coverage>=90", coverage >= 90), ("identity>=95", identity >= 95),
              ("colinear>=90", colinear >= 90), ("truth>=80", truth >= 80)]
    for name, passed in checks:
        log(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    verdict = all(p for _, p in checks)
    log(f"SPIKE VERDICT: {'LIFTOVER FEASIBLE — 完整版方案5 可立项' if verdict else 'LIFTOVER NOT TRUSTWORTHY — 维持轻量版方案5'}")


if __name__ == "__main__":
    main()
