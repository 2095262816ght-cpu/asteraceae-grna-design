# -*- coding: utf-8 -*-
"""16_prep_expression_features.py — 表达数据标准化 + LSA↔T2T 生产版 crosswalk（方案1/3/5 前置）

依据 docs/plans/multiomics_implementation_plan.md（0923 修订版）与 0923 crosswalk 对比实验结论
（_scratch/crosswalk_compare.py 的 v3 分层设计）：

产物
----
1. results/lettuce_gene_expression_features.parquet
   莴苣 40,267 基因（LSA 键）× 5 组织：log2(TPM+1)、组织最大/均值、Tau 特异性指数、
   以及由 16 文库生物学重复表计算的 CV。
2. results/feature_matrix_multiomics_tks.csv
   橡胶草 36,239 基因 × 5 组织均值/log2、Tau、发育均值、CV。
   S9 胶乳列口径固定：`S9-2jiaoru` 视作 rep2，`S9-jiaoruRNA7-3` 排除（来源不明）。
3. results/crosswalk_lsa_t2t_0923.csv
   49 个 demo NLR 基因（LsaT2T* 命名空间）→ LSA 的分层映射，含投票占比、串联簇成员、
   scaffold 命中位置与 unmappable 标记。
4. results/crosswalk_lsa_t2t_report_0923.md — 映射审计（覆盖率、失败清单、口径说明）。

分层映射设计（对比实验定案）
---------------------------
tier1  方法A 锚点投票 offset → 本染色体 ±20kb 窗口内精配/≤2 错配；
tier2  本染色体无界精配（每基因封顶 60 条 guide）；
tier3  v1.1c 未挂载 scaffold 无界精配（封顶 8 条 guide，需 ≥3/8 同区共识）——
       救回「基因座被留在 scaffold 上」的情形（实测 LsaT2T04G000980 → HiC_scaffold_15/LSA112）；
tier4  标记 unmappable，不硬猜（实测两类：v1.1c 序列缺失/高度分歧；序列在但注释缺口）。
解析一律使用启动子感知区间（TSS 上游 2000bp + 基因本体，见 scripts/07 的扫描设计），
串联重复簇记录全部簇成员而非假装 1:1。

运行（crispr 环境）：
    python scripts/16_prep_expression_features.py            # 全量 49 基因
    XWALK_GENES=LsaT2T01G023690 python scripts/16_...py      # 子集冒烟
"""

import bisect
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
LETTUCE_EXPR = BASE_DIR / "data/expression/1-3_lettuce_5tissue_expression_matrix.csv"
LETTUCE_BIOREP = BASE_DIR / "data/expression/lettuce_biorep_expression_matrix.csv"
TKS_EXPR = BASE_DIR / "data/expression/2-3_TKS_Tiss-Dev-Expression(1).xlsx"
V11C_FA = BASE_DIR / "data/reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa"
V11C_GFF = BASE_DIR / "data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff"
T2T_FA = BASE_DIR / "data/reference_genomes/3-1_LsT2T.genome.fa"
GUIDES_CSV = BASE_DIR / "demo/app_data.csv"
GENES_CSV = BASE_DIR / "demo/app_genes.csv"

OUT_LETTUCE = BASE_DIR / "results/lettuce_gene_expression_features.parquet"
OUT_TKS = BASE_DIR / "results/feature_matrix_multiomics_tks.csv"
OUT_XWALK = Path(os.environ.get("XWALK_OUT", str(BASE_DIR / "results/crosswalk_lsa_t2t_0923.csv")))
OUT_XWALK_REPORT = Path(os.environ.get(
    "XWALK_REPORT_OUT", str(BASE_DIR / "results/crosswalk_lsa_t2t_report_0923.md")))

LETTUCE_TISSUES = ["Root", "Stem", "Leaf", "Flower", "Seed"]
PROMOTER_BP = 2000
NEAR_BP = 2000
WINDOW_B = 20000
WINDOW_A = 2000
WINDOW_T2T = 20000
N_SEED_GUIDES = 8
CAP_TIER2 = 25
CAP_TIER3 = 6
CAP_T2_FULL = 40
MAX_LOCUS_BP = 300_000
MAX_FINE_ANCHORS = 3000
TIER3_CONSENSUS = 3
LOW_RESOLUTION = 0.2

# TKS S9 胶乳列人工裁定（0923 实测 79 列，非方案文档所称 80）
TKS_COLUMN_OVERRIDES = {"S9-2jiaoru": ("S9", "jiaoru", "2")}
TKS_COLUMN_EXCLUDES = {"S9-jiaoruRNA7-3"}


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
# 1. 莴苣表达特征库（LSA 键）
# --------------------------------------------------------------------------
def build_lettuce_features():
    df = pd.read_csv(LETTUCE_EXPR)
    assert list(df.columns[:6]) == ["GeneID"] + LETTUCE_TISSUES, df.columns[:6]
    tpm = df[LETTUCE_TISSUES].astype(float)
    out = pd.DataFrame({"GeneID": df["GeneID"].astype(str)})
    for t in LETTUCE_TISSUES:
        out[f"log2_{t.lower()}"] = np.log2(tpm[t].clip(lower=0) + 1.0)
    out["tpm_max"] = tpm.max(axis=1)
    out["e_max_log2"] = np.log2(out["tpm_max"] + 1.0)
    out["e_mean_log2"] = np.log2(tpm.mean(axis=1) + 1.0)
    mx = tpm.max(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        tau = (1.0 - tpm.div(mx, axis=0)).sum(axis=1) / (len(LETTUCE_TISSUES) - 1)
    out["tau"] = tau.where(mx > 0, np.nan)

    bio = pd.read_csv(LETTUCE_BIOREP)
    assert bio.columns[0] == "GeneID"
    libs = bio.columns[1:]
    bnum = bio[libs].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    mu, sd = bnum.mean(axis=1), bnum.std(axis=1)
    cv = (sd / (mu + 1e-9)).rename("cv_biorep")
    out = out.merge(pd.DataFrame({"GeneID": bio["GeneID"].astype(str), "cv_biorep": cv.values}),
                    on="GeneID", how="left", validate="1:1")
    assert len(out) == len(df)
    out.to_parquet(OUT_LETTUCE, index=False)
    log(f"[1] 莴苣表达特征库: {len(out)} 基因 -> {OUT_LETTUCE.name} "
        f"(tau 中位 {out['tau'].median():.3f}, 静默基因占比 "
        f"{100 * (out['tpm_max'] < 0.5).mean():.1f}%)")
    return out


# --------------------------------------------------------------------------
# 2. 橡胶草表达特征表（TKS 键）
# --------------------------------------------------------------------------
def build_tks_features():
    raw = pd.read_excel(TKS_EXPR)
    raw.columns = [str(c).strip() for c in raw.columns]
    gcol = raw.columns[0]
    sample_cols = [c for c in raw.columns[1:]]
    parsed, excluded = {}, []
    for c in sample_cols:
        if c in TKS_COLUMN_EXCLUDES:
            excluded.append(c)
            continue
        if c in TKS_COLUMN_OVERRIDES:
            parsed[c] = TKS_COLUMN_OVERRIDES[c]
            continue
        parts = c.split("-")
        assert len(parts) == 3, f"无法解析 TKS 样本列名: {c}"
        parsed[c] = tuple(parts)
    tissues = sorted({v[1] for v in parsed.values()})
    for c in sample_cols:
        raw[c] = pd.to_numeric(raw[c], errors="coerce").fillna(0.0)

    used = [c for c in parsed]
    tm = pd.DataFrame({t: raw[[c for c in used if parsed[c][1] == t]].mean(axis=1)
                       for t in tissues})
    out = pd.DataFrame({"gene_id": raw[gcol].astype(str).str.strip()})
    assert not out["gene_id"].duplicated().any()
    for t in tissues:
        out[f"tpm_{t}"] = tm[t].values
        out[f"log2_{t}"] = np.log2(tm[t].clip(lower=0) + 1.0).values
    out["dev_mean_tpm"] = raw[used].mean(axis=1).values
    out["dev_mean_log2"] = np.log2(out["dev_mean_tpm"] + 1.0)
    mx = tm.max(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        tau = (1.0 - tm.div(mx, axis=0)).sum(axis=1) / (len(tissues) - 1)
    out["tau"] = tau.where(mx > 0, np.nan).values
    mu = raw[used].mean(axis=1)
    sd = raw[used].std(axis=1)
    out["cv"] = (sd / (mu + 1e-9)).values
    out.to_csv(OUT_TKS, index=False)
    log(f"[2] TKS 表达特征表: {len(out)} 基因 x 组织 {tissues} -> {OUT_TKS.name} "
        f"(采用 {len(used)} 列, 排除 {excluded})")
    return out


# --------------------------------------------------------------------------
# 3. crosswalk 基础设施
# --------------------------------------------------------------------------
def load_v11c_genes():
    recs = defaultdict(list)
    with open(V11C_GFF, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 9 or f[2] != "gene":
                continue
            tag = [x for x in f[8].split(";") if x.startswith("ID=")]
            if not tag:
                continue
            s, e, st = int(f[3]), int(f[4]), f[6]
            es, ee = (s - PROMOTER_BP, e) if st == "+" else (s, e + PROMOTER_BP)
            recs[f[0]].append((max(es, 1), ee, tag[0][3:].replace(":gene", "")))
    idx = {}
    for k, lst in recs.items():
        lst.sort()
        idx[k] = ([r[0] for r in lst], lst)
    return idx


def resolve_lsa(idx, seqname, pos):
    if seqname not in idx or pos is None:
        return None, None, None
    starts, lst = idx[seqname]
    i = bisect.bisect_right(starts, pos) - 1
    if i >= 0:
        es, ee, lsa = lst[i]
        if es <= pos <= ee:
            return lsa, 0, "contained"
    best, bestd = None, None
    for j in (i - 1, i, i + 1):
        if 0 <= j < len(lst):
            es, ee, lsa = lst[j]
            d = 0 if es <= pos <= ee else (es - pos if pos < es else pos - ee)
            if bestd is None or d < bestd:
                best, bestd = lsa, d
    if bestd is not None and bestd <= NEAR_BP:
        return best, bestd, "nearest"
    return None, bestd, "intergenic"


def find_all(s, needle, lo=0, hi=None):
    hi = len(s) if hi is None else min(hi, len(s))
    out, p = [], s.find(needle, lo, hi)
    while p >= 0:
        out.append(p)
        p = s.find(needle, p + 1, hi)
    return out


def locate_20mer(chrom_str, seq20, prefer_strand, bounds=None, max_mis=0):
    lo, hi = bounds if bounds else (0, len(chrom_str))
    rc = str(Seq(seq20).reverse_complement())
    order = [(prefer_strand, seq20 if prefer_strand == "+" else rc),
             ("-" if prefer_strand == "+" else "+", rc if prefer_strand == "+" else seq20)]
    for strand, target in order:
        for off in (0, 8, 4):
            sd = target[off:off + 12]
            for p in find_all(chrom_str, sd, lo, hi):
                start = p - off
                if start < lo or start + 20 > hi:
                    continue
                mis = sum(1 for a, b in zip(chrom_str[start:start + 20], target) if a != b)
                if mis <= max_mis:
                    return start, strand, mis
    return None


def locate_graded(chrom_str, seq20, strand, bounds=None, allow_full=True):
    """Windowed exact -> windowed <=2 mismatch -> (optionally) unbounded exact.

    allow_full=False 时窗口失败直接返回 None，由调用方按封顶策略决定是否付无界代价。
    无界精配约 3 秒/条（6 次 259Mb 全扫），若不封顶，"有 offset 但窗口打不中"的基因
    会按 guide 数线性爆炸（实测 280 条 ≈ 14 分钟）。
    """
    if bounds is not None:
        for mm in (0, 2):
            h = locate_20mer(chrom_str, seq20, strand, bounds=bounds, max_mis=mm)
            if h:
                return h, "window", mm
        if not allow_full:
            return None, None, None
    h = locate_20mer(chrom_str, seq20, strand, max_mis=0)
    if h:
        return h, "full", 0
    return None, None, None


def anchor_offsets(cstr, seq, ts, offset=None):
    offsets = Counter()
    n = 0
    for t in ts:
        if t + 40 > len(seq):
            continue
        anc = seq[t:t + 40]
        rca = str(Seq(anc).reverse_complement())
        n += 1
        for strand, needle, tgt in (("+", anc[:20], anc), ("-", rca[:20], rca)):
            if offset is None:
                lo, hi = 0, None
            else:
                q_pred = t + offset if strand == "+" else t + offset - 39
                lo, hi = max(q_pred - WINDOW_A, 0), q_pred + WINDOW_A + 40
            for p in find_all(cstr, needle, lo, hi):
                q = p if strand == "+" else p - 20
                if q < 0 or q + 40 > len(cstr):
                    continue
                mis = sum(1 for a, b in zip(cstr[q:q + 40], tgt) if a != b)
                if mis <= 1:
                    offsets[(q + (0 if strand == "+" else 39) - t, strand)] += 1
    return offsets, n


# --------------------------------------------------------------------------
# 4. crosswalk 主流程
# --------------------------------------------------------------------------
def run_crosswalk(expr_ids):
    idx = load_v11c_genes()
    genes = pd.read_csv(GENES_CSV)
    guides = pd.read_csv(GUIDES_CSV)
    only = os.environ.get("XWALK_GENES", "")
    sample = [g for g in only.split(",") if g] if only else list(genes.gene_id)
    gsub = guides[guides.gene_id.isin(sample)].copy()
    gsub["seq20"] = gsub["seq20"].str.upper()
    log(f"[3] crosswalk: {len(sample)} 基因, {len(gsub)} guides")

    t2t = Fasta(str(T2T_FA))
    v11c = Fasta(str(V11C_FA))
    scaffold_keys = [k for k in v11c.keys() if not k.startswith("Chr")]
    log(f"    v1.1c seqnames: {len(v11c.keys())} (scaffold {len(scaffold_keys)})")
    t2t_cache, v11c_cache = {}, {}

    def t2t_chrom(c):
        k = c.replace("Chr0", "Chr")
        if k not in t2t_cache:
            t2t_cache[k] = str(t2t[k][:]).upper()
        return t2t_cache[k]

    def v11c_seq(k):
        if k not in v11c_cache:
            v11c_cache[k] = str(v11c[k][:]).upper()
        return v11c_cache[k]

    rows = []
    for chrom in [f"Chr{i:02d}" for i in range(1, 10)]:
        gs = [g for g in sample if gsub[gsub.gene_id == g].iloc[0].chrom == chrom]
        if not gs:
            continue
        log(f"\n  === {chrom}: {len(gs)} 基因 ===")
        cstr = v11c_seq(chrom)

        # 4.1 T2T 定位与稳健基因座（仅本染色体，处理后释放）
        guide_t2t, locus = {}, {}
        for gid in gs:
            sub = gsub[gsub.gene_id == gid]
            s = t2t_chrom(chrom)
            offs, pos, n_full = [], [], 0
            for i, (_, r) in enumerate(sub.iterrows()):
                if i < N_SEED_GUIDES or not offs:
                    h, where, mm = locate_graded(s, r.seq20, r.strand)
                    n_full += 1
                else:
                    pred = int(r.start) + int(np.median(offs))
                    h, where, mm = locate_graded(
                        s, r.seq20, r.strand,
                        bounds=(max(pred - WINDOW_T2T, 0), pred + WINDOW_T2T),
                        allow_full=False)
                    if h is None and n_full < CAP_T2_FULL:
                        n_full += 1
                        h, where, mm = locate_graded(s, r.seq20, r.strand)
                if h:
                    guide_t2t[r.guide_id] = (h[0], h[1])
                    pos.append(h[0])
                    offs.append(h[0] - int(r.start))
            if len(pos) >= 3:
                lo = max(int(np.percentile(pos, 10)) - 5000, 0)
                hi = min(int(np.percentile(pos, 90)) + 5000, len(s))
                if hi - lo > MAX_LOCUS_BP:
                    # p10-p90 对双峰/散乱命中会退化成整条染色体（实测 83Mb/200Mb），
                    # 使 fine-anchor 阶段扫上百万锚点。此时改用覆盖 >=60% 命中的最窄窗口；
                    # 仍过宽则弃用基因座（该基因走 tier2 封顶路径，最终多被判 unmappable）。
                    pos_s = np.sort(np.asarray(pos))
                    need = max(3, int(0.6 * len(pos_s)))
                    widths = pos_s[need - 1:] - pos_s[:len(pos_s) - need + 1]
                    j = int(np.argmin(widths))
                    lo, hi = int(pos_s[j]), int(pos_s[j + need - 1])
                    if hi - lo > MAX_LOCUS_BP:
                        locus[gid] = None
                        log(f"    T2T 基因座 {gid}: 命中双峰且主导簇过宽，弃用基因座")
                        continue
                    lo, hi = max(lo - 5000, 0), min(hi + 5000, len(s))
                locus[gid] = (chrom, lo, hi)
            else:
                locus[gid] = None
            log(f"    T2T 基因座 {gid}: {locus[gid] if locus[gid] else 'NONE'} "
                f"(命中 {len(pos)}/{len(sub)}, 全扫 {n_full})")

        # 4.2 锚点投票 offset
        offsets = {}
        for gid in gs:
            L = locus.get(gid)
            offsets[gid] = None
            if not L:
                continue
            seq = t2t_chrom(chrom)[L[1]:L[2]]
            step = max(1, len(seq) // 12)
            coarse, nc = anchor_offsets(cstr, seq, range(0, max(1, len(seq) - 40), step))
            if not coarse:
                continue
            (d0, st0), c0 = coarse.most_common(1)[0]
            fine_step = max(100, len(seq) // MAX_FINE_ANCHORS)
            fine, nf = anchor_offsets(cstr, seq, range(0, max(1, len(seq) - 40), fine_step),
                                      offset=d0)
            (d, st), cnt = (fine.most_common(1)[0] if fine else ((d0, st0), c0))
            offsets[gid] = {"d": d, "lo": L[1], "consistency": cnt / max(nf, 1)}
        del t2t_cache[chrom.replace("Chr0", "Chr")]

        # 4.3 分层 guide 映射
        for gid in gs:
            sub = gsub[gsub.gene_id == gid]
            a = offsets[gid]
            votes = Counter()
            tier_used, n_t2 = 1, 0
            scaf_note = ""
            for _, r in sub.iterrows():
                t2 = guide_t2t.get(r.guide_id)
                h = None
                if a and t2:
                    pred = t2[0] - a["lo"] + a["d"]
                    h, where, mm = locate_graded(
                        cstr, r.seq20, r.strand,
                        bounds=(max(pred - WINDOW_B, 0), pred + WINDOW_B + 20),
                        allow_full=False)
                if h is None:
                    if n_t2 >= CAP_TIER2:
                        continue
                    n_t2 += 1
                    h, where, mm = locate_graded(cstr, r.seq20, r.strand)
                    tier_used = max(tier_used, 2)
                if h:
                    lsa, d, how = resolve_lsa(idx, chrom, h[0] + 10)
                    if lsa:
                        votes[(lsa, how)] += 1
            resolved_frac = sum(votes.values()) / max(len(sub), 1)

            # tier3：仅当本染色体基本解析失败时才做 scaffold 搬迁排查
            if resolved_frac < LOW_RESOLUTION:
                hits, scaf_hits, loaded = [], Counter(), set()
                for _, r in sub.head(CAP_TIER3).iterrows():
                    s20, rc = r.seq20, str(Seq(r.seq20).reverse_complement())
                    for k in scaffold_keys:
                        seq = v11c_seq(k)
                        loaded.add(k)
                        p = seq.find(s20)
                        strand = "+"
                        if p < 0:
                            p, strand = seq.find(rc), "-"
                        if p >= 0:
                            hits.append((k, p, strand))
                            scaf_hits[k] += 1
                            break
                for k in loaded:
                    del v11c_cache[k]
                cons = scaf_hits.most_common(1)
                if cons and cons[0][1] >= TIER3_CONSENSUS:
                    k = cons[0][0]
                    for kk, p, strand in hits:
                        if kk == k:
                            lsa, d, how = resolve_lsa(idx, k, p + 10)
                            if lsa:
                                votes[(lsa, how)] += 1
                    tier_used = 3
                    scaf_note = f"{cons[0][0]}:{cons[0][1]}/{min(CAP_TIER3, len(sub))}"

            # 守卫：解析占比过低且 tier3 未救回 => 弱票作废，标记 unmappable，不硬凑答案
            rescued = tier_used == 3
            voided = (resolved_frac < LOW_RESOLUTION) and not rescued
            if voided:
                votes = Counter()

            top = votes.most_common(1)
            lsa_votes = Counter()
            for (lsa, how), v in votes.items():
                lsa_votes[lsa] += v
            total_votes = max(sum(lsa_votes.values()), 1)
            prim = lsa_votes.most_common(1)
            cluster = [f"{lsa}:{v}" for lsa, v in lsa_votes.most_common()
                       if v >= 0.1 * total_votes]
            primary = prim[0][0] if prim else None
            rows.append({
                "gene_id": gid, "chrom_delivered": chrom, "n_guides": len(sub),
                "tier": tier_used if primary else 4,
                "lsa_primary": primary,
                "lsa_primary_mode": top[0][0][1] if top else None,
                "lsa_vote_frac": round(prim[0][1] / total_votes, 3) if prim else 0.0,
                "lsa_resolved_frac": round(resolved_frac, 3),
                "lsa_cluster": ";".join(cluster),
                "n_cluster": len(cluster),
                "scaffold_evidence": scaf_note,
                "voided_low_resolution": bool(voided),
                "offset_consistency": round(a["consistency"], 3) if a else None,
                "in_expression_matrix": bool(primary in expr_ids) if primary else False,
            })
            log(f"    {gid}: tier{rows[-1]['tier']} -> {primary} "
                f"(vote {rows[-1]['lsa_vote_frac']}, resolved {rows[-1]['lsa_resolved_frac']}, "
                f"cluster {rows[-1]['n_cluster']}"
                f"{', scaf ' + scaf_note if scaf_note else ''}"
                f"{', 弱票作废' if voided else ''})")
        del v11c_cache[chrom]

    df = pd.DataFrame(rows)
    df.to_csv(OUT_XWALK, index=False)
    return df, scaffold_keys


def write_crosswalk_report(df):
    ok = df[df["lsa_primary"].notna() & df["in_expression_matrix"]]
    bad = df[~df["lsa_primary"].notna() | ~df["in_expression_matrix"]]
    lines = [
        "# LSA↔T2T crosswalk 审计（0923）",
        "",
        f"> 生成脚本：`scripts/16_prep_expression_features.py`",
        f"> 样本：{len(df)} 个 demo NLR 基因（`demo/app_data.csv` 的 LsaT2T* 命名空间）",
        "",
        "## 一、覆盖率",
        "",
        f"- 可映射且在表达矩阵中：**{len(ok)}/{len(df)}（{100 * len(ok) / len(df):.1f}%）**",
        f"- 不可映射：{len(bad)} 个（见第三节）",
        f"- 分层使用分布：{df['tier'].value_counts().sort_index().to_dict()}",
        "",
        "## 二、映射主表",
        "",
        "| 基因 | 染色体 | tier | LSA 主映射 | 投票占比 | 解析占比 | 簇大小 | scaffold 证据 |",
        "|---|---|---:|---|---:|---:|---:|---|",
    ]
    for _, r in df.iterrows():
        lines.append(f"| `{r['gene_id']}` | {r['chrom_delivered']} | {r['tier']} | "
                     f"{r['lsa_primary'] or '—'} | {r['lsa_vote_frac']:.2f} | "
                     f"{r['lsa_resolved_frac']:.2f} | {r['n_cluster']} | "
                     f"{r['scaffold_evidence'] or '—'} |")
    lines += [
        "",
        "## 三、不可映射清单与原因分类",
        "",
    ]
    if len(bad) == 0:
        lines.append("（无）")
    for _, r in bad.iterrows():
        lines.append(f"- `{r['gene_id']}`："
                     f"{'弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；' if r.get('voided_low_resolution') else ''}"
                     f"解析占比 {r['lsa_resolved_frac']:.2f}，"
                     f"scaffold 排查 {r['scaffold_evidence'] or '无共识'}。原因类别见下注。")
    lines += [
        "",
        "原因类别（0923 对比实验实测）：",
        "1. **序列缺失/高度分歧**：本染色体与 scaffold 均无精配命中（如 `LsaT2T01G030600`）；",
        "2. **v1.1c 注释缺口**：序列共线命中但最近基因模型 > 2kb（如 `LsaT2T05G000020`）；",
        "3. **scaffold 搬迁**：可由 tier3 救回（如 `LsaT2T04G000980` → `HiC_scaffold_15`/LSA112）。",
        "",
        "## 四、口径与方法说明",
        "",
        "- 解析区间为启动子感知：`[start-2000, end]`（+ 链）/ `[start, end+2000]`（− 链），"
        "与 `scripts/07` 的扫描设计（TSS 上游 2000bp + 全部外显子）一致；nearest 仅在 2kb 内；",
        "- 串联重复簇（NLR）记录 `lsa_cluster` 全部成员（投票 ≥10%），**不假设 1:1**；",
        "- tier1 窗口依赖锚点投票 offset；tier2/3 均有封顶，最坏代价有界；",
        "- 失败是可检测的：两类不可映射基因在 tier1/tier2 同时退化，不会被硬凑成错误答案。",
    ]
    OUT_XWALK_REPORT.write_text("\n".join(lines), encoding="utf-8")
    log(f"[4] crosswalk 审计报告 -> {OUT_XWALK_REPORT.name}")


def main():
    if os.environ.get("XWALK_ONLY"):
        lettuce_ids = set(pd.read_parquet(OUT_LETTUCE)["GeneID"])
    else:
        lettuce_ids = set(build_lettuce_features()["GeneID"])
        build_tks_features()
    df, _ = run_crosswalk(lettuce_ids)
    write_crosswalk_report(df)
    log("\n完成。")


if __name__ == "__main__":
    main()
