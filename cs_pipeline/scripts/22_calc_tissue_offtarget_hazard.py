# -*- coding: utf-8 -*-
"""22_calc_tissue_offtarget_hazard.py — 方案5（轻量版）：面板内组织功能性脱靶危害指数

范围声明（0923 定版）
--------------------
完整版方案5 需要 608 万脱靶位点底层大表与 T2T→v1.1c 全基因组 liftover，两者当前均不具备
（位点大表与按染色体扫描参考都已不在磁盘上）。轻量版将危害评估限定在**49 个 demo NLR
靶基因座之间**的 collateral 切割：这些基因座是经 scripts/16 crosswalk 映射、有 v1.1c 表达值
的唯一区域。面板外位点（含管家/光合基因）的危害本版不评估，文档如实标注。

数学模型（方案文档原式，作用于面板内位点）
------------------------------------------
    Hazard_t(g) = Σ_{k ∈ intra-panel hits(g)} ω(mis_k) · [1 + λ · log2(TPM_t(gene(k)) + 1)]
    ω(0)=10, ω(1)=3, ω(2)=1, ω(3)=0.2；λ=0.5
    gene(k) 取该基因座的 crosswalk 主映射 LSA；不可映射基因座按背景基线 0.1 计。
    guide 自身 on-target 位点（本基因座内、0 错配、自身坐标）不计入。

位点发现：鸽笼原理种子筛——20-mer 上 ≤3 错配 ⇒ 4 个互不重叠 5-mer 块必有一块精配；
对每个基因座建 5-mer 位置索引（双链），逐 guide 查 4 块、验证 NGG PAM 与 Hamming ≤3。

运行：python scripts/22_calc_tissue_offtarget_hazard.py
产物：results/offtarget_functional_hazard_0923.csv
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
GUIDES_CSV = BASE_DIR / "demo" / "app_data.csv"
XWALK_CSV = BASE_DIR / "results" / "crosswalk_lsa_t2t_0923.csv"
EXPR_CSV = BASE_DIR / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"
T2T_FA = BASE_DIR / "data" / "reference_genomes" / "3-1_LsT2T.genome.fa"
OUT = BASE_DIR / "results" / "offtarget_functional_hazard_0923.csv"

TISSUES = ["Root", "Stem", "Leaf", "Flower", "Seed"]
OMEGA = {0: 10.0, 1: 3.0, 2: 1.0, 3: 0.2}
LAM = 0.5
BACKGROUND = 0.1
MAX_MIS = 3
BLOCK = 5
WINDOW_T2T = 20000
N_SEED_GUIDES = 8


def log(msg):
    print(msg, flush=True)


def locate_exact(chrom_str, seq20, strand, bounds=None):
    target = seq20 if strand == "+" else str(Seq(seq20).reverse_complement())
    lo, hi = bounds if bounds else (0, len(chrom_str))
    for off in (0, 8, 4):
        for p in _find_all(chrom_str, target[off:off + 12], lo, hi):
            start = p - off
            if lo <= start and start + 20 <= hi and chrom_str[start:start + 20] == target:
                return start
    return None


def _find_all(s, needle, lo, hi):
    out, p = [], s.find(needle, lo, hi)
    while p >= 0:
        out.append(p)
        p = s.find(needle, p + 1, hi)
    return out


def localize_loci(guides):
    """复刻 scripts/16 的 T2T 定位：返回 {gene: (chrom, lo, hi)} 与 {guide_id: (chrom, pos)}。"""
    t2t = Fasta(str(T2T_FA))
    cache = {}
    locus, guide_pos = {}, {}
    for gid, sub in guides.groupby("gene_id"):
        chrom = sub.iloc[0].chrom
        k = chrom.replace("Chr0", "Chr")
        if k not in cache:
            cache[k] = str(t2t[k][:]).upper()
        s = cache[k]
        offs, pos = [], []
        for i, (_, r) in enumerate(sub.iterrows()):
            if i < N_SEED_GUIDES or not offs:
                p = locate_exact(s, r.seq20, r.strand)
            else:
                pred = int(r.start) + int(np.median(offs))
                p = locate_exact(s, r.seq20, r.strand,
                                 bounds=(max(pred - WINDOW_T2T, 0), pred + WINDOW_T2T))
            if p is not None:
                guide_pos[r.guide_id] = (k, p)
                pos.append(p)
                offs.append(p - int(r.start))
        if len(pos) >= 3:
            lo = max(int(np.percentile(pos, 10)) - 5000, 0)
            hi = min(int(np.percentile(pos, 90)) + 5000, len(s))
            if hi - lo > MAX_LOCUS_BP:
                # 双峰/散乱命中使 p10-p90 退化（实测可达 80Mb+），5-mer 索引会爆炸；
                # 取覆盖 >=60% 命中的最窄窗口，仍过宽则放弃该基因座（与 scripts/16 同守卫）
                pos_s = np.sort(np.asarray(pos))
                need = max(3, int(0.6 * len(pos_s)))
                widths = pos_s[need - 1:] - pos_s[:len(pos_s) - need + 1]
                j = int(np.argmin(widths))
                lo2, hi2 = int(pos_s[j]), int(pos_s[j + need - 1])
                if hi2 - lo2 > MAX_LOCUS_BP:
                    locus[gid] = None
                    log(f"    [warn] {gid}: 命中双峰且主导簇过宽，跳过该基因座的面板内扫描")
                    continue
                lo, hi = max(lo2 - 5000, 0), min(hi2 + 5000, len(s))
            locus[gid] = (k, lo, hi)
        else:
            locus[gid] = None
        del s
    return locus, guide_pos, cache


MAX_LOCUS_BP = 300_000


def build_kmer_index(seq):
    idx = defaultdict(list)
    n = len(seq)
    for p in range(n - BLOCK + 1):
        idx[seq[p:p + BLOCK]].append(p)
    return idx


def scan_guide_against_locus(g20, plus, minus, idx_plus, idx_minus):
    """返回 [(pos_plus, strand, mis)]：面板内与该 guide ≤3 错配且带 NGG PAM 的位点。

    plus/minus 为基因座双链字符串（minus = rc(plus)，长度 n）。
    各链候选在自身坐标系内验证 PAM（链上 3' 紧邻 NGG），minus 命中再换算回 plus 坐标。
    """
    n = len(plus)
    hits = []
    cands = set()
    for off, b in zip((0, 5, 10, 15), (g20[0:5], g20[5:10], g20[10:15], g20[15:20])):
        for p in idx_plus.get(b, ()):
            cands.add((p - off, "+"))
        for q in idx_minus.get(b, ()):
            cands.add((q - off, "-"))
    for c, strand in cands:
        if c < 0 or c + 20 > n:
            continue
        if strand == "+":
            if plus[c + 21:c + 23] != "GG":
                continue
            target = plus[c:c + 20]
            pos = c
        else:
            if c + 23 > n or minus[c + 21:c + 23] != "GG":
                continue
            target = minus[c:c + 20]
            pos = n - c - 20
        mis = sum(1 for a, b in zip(g20, target) if a != b)
        if mis <= MAX_MIS:
            hits.append((pos, strand, mis))
    return hits


def main():
    guides = pd.read_csv(GUIDES_CSV)
    guides["seq20"] = guides["seq20"].str.upper()
    xw = pd.read_csv(XWALK_CSV).set_index("gene_id")
    expr = pd.read_csv(EXPR_CSV).set_index("GeneID")

    log(f"[1] 定位 49 个面板基因座于本地 T2T 基因组 …")
    locus, guide_pos, cache = localize_loci(guides)
    n_loc = sum(1 for v in locus.values() if v)
    log(f"    基因座 {n_loc}/{len(locus)} 可定位")

    log("[2] 鸽笼种子筛：逐基因座扫描全部 guide …")
    site_rows = []
    all_guides = list(zip(guides.guide_id, guides.seq20))
    for gid, L in locus.items():
        if not L:
            continue
        k, lo, hi = L
        plus = cache[k][lo:hi]
        minus = str(Seq(plus).reverse_complement())
        idx_plus = build_kmer_index(plus)
        idx_minus = build_kmer_index(minus)
        sub = guides[guides.gene_id == gid]
        own = {r.guide_id for _, r in sub.iterrows()}
        own_pos = {r.guide_id: guide_pos[r.guide_id][1] for _, r in sub.iterrows()
                   if r.guide_id in guide_pos}
        for g_id, g20 in all_guides:
            hits = scan_guide_against_locus(g20, plus, minus, idx_plus, idx_minus)
            for p, strand, mis in hits:
                if mis == 0 and g_id in own and g_id in own_pos and abs(own_pos[g_id] - (lo + p)) <= 3:
                    continue  # 自身 on-target
                site_rows.append({"guide_id": g_id, "hit_gene": gid,
                                  "pos_in_locus": p, "strand": strand, "mis": mis})
        log(f"    {gid}: 累计面板内位点 {len(site_rows)}")
        del idx_plus, idx_minus

    sites = pd.DataFrame(site_rows)
    log(f"[3] 面板内位点总数 {len(sites)}（mis 分布 "
        f"{sites.mis.value_counts().sort_index().to_dict() if len(sites) else {}}）")

    log2tpm = {t: np.log2(expr[t].clip(lower=0) + 1.0) for t in TISSUES}
    recs = []
    if len(sites):
        sites = sites.assign(
            lsa=sites.hit_gene.map(xw["lsa_primary"]),
            omega=sites.mis.map(OMEGA))
        for t in TISSUES:
            factor = sites.lsa.map(
                lambda l: BACKGROUND if (not isinstance(l, str) or l not in expr.index)
                else 1.0 + LAM * float(log2tpm[t][l]))
            sites[f"w_{t}"] = sites.omega * factor
        per = sites.groupby("guide_id").agg(
            **{f"hazard_{t.lower()}": (f"w_{t}", "sum") for t in TISSUES},
            n_intra_panel_sites=("mis", "size"),
            mis0=("mis", lambda s: int((s == 0).sum())),
            mis1=("mis", lambda s: int((s == 1).sum())),
            mis2=("mis", lambda s: int((s == 2).sum())),
            mis3=("mis", lambda s: int((s == 3).sum())),
        ).reset_index()
    else:
        per = pd.DataFrame(columns=["guide_id"] + [f"hazard_{t.lower()}" for t in TISSUES]
                           + ["n_intra_panel_sites", "mis0", "mis1", "mis2", "mis3"])
    out = guides[["guide_id", "gene_id"]].merge(per, on="guide_id", how="left")
    for c in [f"hazard_{t.lower()}" for t in TISSUES] + ["n_intra_panel_sites",
                                                          "mis0", "mis1", "mis2", "mis3"]:
        out[c] = out[c].fillna(0.0)
    out.to_csv(OUT, index=False)
    log(f"[4] 危害分 -> {OUT.name}")
    log(f"    hazard_leaf 分布: 0 值 {int((out.hazard_leaf == 0).sum())} 条, "
        f"中位 {out.hazard_leaf.median():.1f}, P95 {out.hazard_leaf.quantile(0.95):.1f}, "
        f"max {out.hazard_leaf.max():.1f}")
    top = out.nlargest(5, "hazard_leaf")[["guide_id", "gene_id", "n_intra_panel_sites",
                                          "mis0", "hazard_leaf"]]
    log(top.to_string(index=False))


if __name__ == "__main__":
    main()
