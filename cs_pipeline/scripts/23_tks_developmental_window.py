# -*- coding: utf-8 -*-
"""23_tks_developmental_window.py — 方案6：橡胶草产胶发育时相最佳编辑转化窗口预测

工序
----
0. 读取橡胶树（Hevea）参考蛋白（data/reference_genomes/tks_rubber_pathway_queries.fasta，
   9 条：REF×3 / SRPP×3 / CPT(HRT)×3，经 EBI dbfetch 获取；获取命令见文件尾注释）。
1. 翻译 TKS 全部 CDS（2-2_TKS.genome.gff3 + 2-1_TKS.genome.fasta）为蛋白。
2. 同源筛选：7-aa 词命中预筛（≥3 词）→ Smith-Waterman 局部比对（identity ≥ 0.35 且
   覆盖度 ≥ 0.50）→ 各家族成员表 results/tks_rubber_family_members_0923.csv。
3. 时相动力学：根 S1–S9、胶乳 S4–S9（S9 胶乳口径固定：S9-2jiaoru=rep2、
   S9-jiaoruRNA7-3 排除）按「重复×家族成员」取均值；三次样条拟合 + 一阶导数定位转录爆发期。
4. 产出：results/tks_pathway_stage_curves_0923.csv（长表，供 demo）、
   results/tks_developmental_window_0923.csv（窗口卡）、
   results/tks_rubber_pathway_dynamics.png（9 时相动态折线图）。

运行：python scripts/23_tks_developmental_window.py
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta
from scipy.interpolate import CubicSpline

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
QUERIES_FA = BASE_DIR / "data" / "reference_genomes" / "tks_rubber_pathway_queries.fasta"
TKS_GFF = BASE_DIR / "data" / "reference_genomes" / "2-2_TKS.genome.gff3"
TKS_FA = BASE_DIR / "data" / "reference_genomes" / "2-1_TKS.genome.fasta"
TKS_EXPR = BASE_DIR / "data" / "expression" / "2-3_TKS_Tiss-Dev-Expression(1).xlsx"

OUT_MEMBERS = BASE_DIR / "results" / "tks_rubber_family_members_0923.csv"
OUT_CURVES = BASE_DIR / "results" / "tks_pathway_stage_curves_0923.csv"
OUT_WINDOW = BASE_DIR / "results" / "tks_developmental_window_0923.csv"
OUT_PNG = BASE_DIR / "results" / "tks_rubber_pathway_dynamics.png"

WORD_K = 5
WORD_STEP = 1
WORD_MIN_HITS = 4
TOP_CANDS = 40
MIN_IDENTITY = 0.30
MIN_COVERAGE = 0.50

TKS_COLUMN_OVERRIDES = {"S9-2jiaoru": ("S9", "jiaoru", "2")}
TKS_COLUMN_EXCLUDES = {"S9-jiaoruRNA7-3"}
FAMILY_CN = {"REF": "REF（橡胶延伸因子）", "SRPP": "SRPP（小橡胶粒子蛋白）",
             "CPT": "CPT/HRT（顺式聚异戊二烯转移酶）"}
# matplotlib 默认字体无 CJK 字形，图内一律英文
FAMILY_EN = {"REF": "REF / rubber elongation factor",
             "SRPP": "SRPP / small rubber particle protein",
             "CPT": "CPT / HRT cis-prenyltransferase"}


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
def read_queries():
    fams = defaultdict(dict)
    fam, acc, seq = None, None, []
    for line in QUERIES_FA.read_text().splitlines():
        if line.startswith(">"):
            if fam and acc:
                fams[fam][acc] = "".join(seq)
            toks = line[1:].split()
            fam, acc, seq = toks[0].split("_")[1], (toks[1] if len(toks) > 1 else toks[0]), []
        else:
            seq.append(line.strip())
    if fam and acc:
        fams[fam][acc] = "".join(seq)
    return dict(fams)


# --------------------------------------------------------------------------
def translate_tks():
    cds = defaultdict(list)
    with open(TKS_GFF, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 9 or f[2] != "CDS":
                continue
            parent = [x for x in f[8].split(";") if x.startswith("Parent=")]
            if not parent:
                continue
            cds[parent[0][7:]].append((f[0], int(f[3]), int(f[4]), f[6]))
    fa = Fasta(str(TKS_FA))
    proteins = {}
    for mrna, feats in cds.items():
        chrom = feats[0][0]
        strand = feats[0][3]
        lo, hi = min(f[1] for f in feats), max(f[2] for f in feats)
        span = str(fa[chrom][lo - 1:hi]).upper()
        parts = []
        for _, s, e, _ in sorted(feats, key=lambda x: x[1]):
            parts.append(span[s - lo:e - lo + 1])
        nuc = "".join(parts)
        nuc = nuc[: len(nuc) // 3 * 3]
        if strand == "-":
            nuc = str(Seq(nuc).reverse_complement())
        prot = str(Seq(nuc).translate(to_stop=True))
        if len(prot) >= 40:
            proteins[mrna] = prot
    log(f"[1] TKS CDS 翻译完成: {len(proteins)} 个蛋白（≥40aa）")
    return proteins


# --------------------------------------------------------------------------
def smith_waterman_simple(a, b):
    """带矩阵存储的 SW（候选量小，内存可接受）。返回 (identity, coverage_of_a)。"""
    n, m = len(a), len(b)
    H = [[0] * (m + 1) for _ in range(n + 1)]
    best = 0
    bi = bj = 0
    for i in range(1, n + 1):
        ai = a[i - 1]
        Hi, Hp = H[i], H[i - 1]
        for j in range(1, m + 1):
            v = max(Hp[j - 1] + (2 if ai == b[j - 1] else -1), Hp[j] - 2, Hi[j - 1] - 2, 0)
            Hi[j] = v
            if v > best:
                best, bi, bj = v, i, j
    if best == 0:
        return 0.0, 0.0
    i, j = bi, bj
    matches = alen = 0
    while i > 0 and j > 0 and H[i][j] > 0:
        sc = 2 if a[i - 1] == b[j - 1] else -1
        if H[i][j] == H[i - 1][j - 1] + sc:
            alen += 1
            if sc == 2:
                matches += 1
            i, j = i - 1, j - 1
        elif H[i][j] == H[i - 1][j] - 2:
            alen += 1
            i -= 1
        else:
            alen += 1
            j -= 1
    return (matches / alen if alen else 0.0), alen / n


# --------------------------------------------------------------------------
def screen_families(fams, proteins):
    rows = []
    prot_ids = list(proteins)
    for fam, queries in fams.items():
        for qname, qseq in queries.items():
            words = [qseq[i:i + WORD_K] for i in range(0, max(0, len(qseq) - WORD_K + 1), WORD_STEP)]
            counts = Counter()
            for pid in prot_ids:
                p = proteins[pid]
                hit = sum(1 for w in words if w in p)
                if hit >= WORD_MIN_HITS:
                    counts[pid] = hit
            cands = counts.most_common(TOP_CANDS)
            for pid, _ in cands:
                ident, cov = smith_waterman_simple(qseq, proteins[pid])
                if ident >= MIN_IDENTITY and cov >= MIN_COVERAGE:
                    rows.append({"family": fam, "query": qname, "tks_gene": pid,
                                 "identity": round(ident, 3), "coverage": round(cov, 3)})
        n = len({r["tks_gene"] for r in rows if r["family"] == fam})
        log(f"[2] 家族 {fam}: 成员 {n} 个 TKS 基因")
    df = pd.DataFrame(rows)
    if len(df):
        df = (df.sort_values("identity", ascending=False)
                .drop_duplicates(["family", "tks_gene"]))
    df.to_csv(OUT_MEMBERS, index=False)
    log(f"    成员表 -> {OUT_MEMBERS.name}（{len(df)} 行）")
    return df


# --------------------------------------------------------------------------
def load_expression():
    raw = pd.read_excel(TKS_EXPR)
    raw.columns = [str(c).strip() for c in raw.columns]
    gcol = raw.columns[0]
    parsed = {}
    for c in raw.columns[1:]:
        if c in TKS_COLUMN_EXCLUDES:
            continue
        parsed[c] = TKS_COLUMN_OVERRIDES.get(c) or tuple(c.split("-"))
    for c in raw.columns[1:]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce").fillna(0.0)
    raw = raw.set_index(raw[gcol].astype(str).str.strip())
    return raw, parsed


def build_curves(members, raw, parsed):
    stages_root = [f"S{i}" for i in range(1, 10)]
    stages_latex = [f"S{i}" for i in range(4, 10)]
    cols_by = defaultdict(list)
    for c, meta in parsed.items():
        cols_by[(meta[0], meta[1])].append(c)

    recs = []
    for fam in ("REF", "SRPP", "CPT"):
        gens = members[members.family == fam].tks_gene.tolist()
        gens = [g for g in gens if g in raw.index]
        if not gens:
            log(f"    [warn] 家族 {fam} 无表达矩阵成员，跳过")
            continue
        sub = raw.loc[gens]
        for tissue, stages in (("gen", stages_root), ("jiaoru", stages_latex)):
            for s in stages:
                cols = cols_by.get((s, tissue), [])
                if not cols:
                    continue
                val = float(sub[cols].values.mean())
                recs.append({"family": fam, "tissue": tissue, "stage": s,
                             "stage_num": int(s[1:]), "n_genes": len(gens),
                             "mean_tpm": round(val, 4)})
    curves = pd.DataFrame(recs)
    curves.to_csv(OUT_CURVES, index=False)
    log(f"[3] 时相曲线 -> {OUT_CURVES.name}（{len(curves)} 行）")
    return curves


def _tissue_stats(t, key, out):
    """按组织写 {key}_* 字段：峰值/首时相/onset(≥50%峰)/爆发期(样条一阶导, 内部网格)。"""
    if len(t) == 0:
        return
    x = t.stage_num.values.astype(float)
    y = t.mean_tpm.values.astype(float)
    out[f"{key}_peak_tpm"] = round(float(y.max()), 2)
    out[f"{key}_peak_stage"] = f"S{int(x[int(np.argmax(y))])}"
    out[f"{key}_first_stage"] = f"S{int(x[0])}"
    base = float(y[0])
    out[f"{key}_fold_peak_vs_first"] = round(float(y.max()) / base, 1) if base > 0 else None
    out[f"{key}_onset_stage"] = f"S{int(x[int(np.argmax(y >= 0.5 * y.max()))])}"
    if len(t) < 4:
        out[f"{key}_burst_stage"] = out[f"{key}_onset_stage"]
        out[f"{key}_trend"] = "too-few-stages"
        return
    cs = CubicSpline(x, y)
    # 爆发期只在「峰值之前的上升段」内取一阶导最大处；否则视为首时相已活跃。
    # 限制在峰前可避免把峰后次要回升（如胶乳 S8->S9 的小反弹）误判为爆发期。
    peak_idx = int(np.argmax(y))
    if peak_idx == 0:
        out[f"{key}_burst_stage"] = f"S{int(x[0])}"
        out[f"{key}_trend"] = "declining-from-first-sample"
        return
    grid = np.linspace(x[0] + 0.25, x[peak_idx] - 0.25, 150) if peak_idx >= 1 else None
    if grid is None or grid.max() <= grid.min():
        out[f"{key}_burst_stage"] = f"S{int(x[0])}"
        out[f"{key}_trend"] = "declining-from-first-sample"
        return
    d = cs(grid, 1)
    if float(d.max()) <= 0:
        out[f"{key}_burst_stage"] = f"S{int(x[0])}"
        out[f"{key}_trend"] = "declining-from-first-sample"
    else:
        out[f"{key}_burst_stage"] = f"S{int(round(float(grid[int(np.argmax(d))])))}"
        out[f"{key}_trend"] = "rising"


def fit_window(curves):
    cards = []
    for fam in curves.family.unique():
        sub = curves[curves.family == fam]
        out = {"family": fam}
        for tissue, key in (("gen", "root"), ("jiaoru", "latex")):
            _tissue_stats(sub[sub.tissue == tissue].sort_values("stage_num"), key, out)
        trend = out.get("latex_trend")
        if trend == "declining-from-first-sample":
            rec = out.get("latex_first_stage")
            why = (f"胶乳通路在首个胶乳采样时相 {rec} 即已高活跃（峰值 "
                   f"{out.get('latex_peak_stage')}），此后单调下降，故诱导应不晚于 {rec}")
        elif trend in ("rising", "too-few-stages"):
            rec = out.get("latex_onset_stage") or out.get("latex_first_stage")
            why = (f"胶乳转录爆发期位于 {out.get('latex_burst_stage')}，onset（≥50% 峰）为 {rec}，"
                   f"在 onset 期诱导兼顾通路活跃度与组织再生能力")
        else:
            rec = out.get("root_onset_stage") or out.get("root_burst_stage")
            why = "无胶乳曲线，参考根爆发期"
        out["recommended_stage"] = rec
        out["card_text"] = (
            f"推荐在 {rec} 期启动 Cas9 诱导表达：{why}；胶乳峰值 "
            f"{out.get('latex_peak_tpm', '—')} TPM（{out.get('latex_peak_stage', '—')}），"
            f"根爆发期 {out.get('root_burst_stage', '—')}、根峰值 "
            f"{out.get('root_peak_tpm', '—')} TPM（{out.get('root_peak_stage', '—')}）。"
        )
        cards.append(out)
    cards_df = pd.DataFrame(cards)
    cards_df.to_csv(OUT_WINDOW, index=False)
    log(f"[4] 窗口卡 -> {OUT_WINDOW.name}")
    for _, r in cards_df.iterrows():
        log(f"    {r['family']}: {r['card_text']}")
    return cards_df


def plot_dynamics(curves, cards):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fams = list(curves.family.unique())
    fig, axes = plt.subplots(1, len(fams), figsize=(5.2 * len(fams), 4.2), sharey=False)
    if len(fams) == 1:
        axes = [axes]
    for ax, fam in zip(axes, fams):
        sub = curves[curves.family == fam]
        for tissue, style, lab in (("gen", "-", "root (gen)"), ("jiaoru", "--", "latex (jiaoru)")):
            t = sub[sub.tissue == tissue].sort_values("stage_num")
            if len(t):
                ax.plot(t.stage_num, t.mean_tpm, style + "o", ms=4, label=lab)
        card = cards[cards.family == fam].iloc[0]
        rec = card.get("recommended_stage")
        if rec:
            ax.axvline(int(rec[1:]), color="#d62728", ls=":", lw=1.5,
                       label=f"recommended {rec}")
        ax.set_title(f"{fam}: {FAMILY_EN.get(fam, fam)}")
        ax.set_xlabel("developmental stage")
        ax.set_ylabel("mean TPM")
        ax.set_xticks(range(1, 10))
        ax.legend(fontsize=8)
    fig.suptitle("Taraxacum kok-saghyz rubber-biosynthesis pathway: S1-S9 dynamics (0923)")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=160)
    plt.close(fig)
    log(f"[5] 动态图 -> {OUT_PNG.name}")


def main():
    assert QUERIES_FA.exists(), (
        f"缺少参考蛋白 {QUERIES_FA}；获取命令见本脚本尾部注释（EBI dbfetch，需代理）")
    fams = read_queries()
    log(f"[0] 参考蛋白家族: { {k: len(v) for k, v in fams.items()} }")
    proteins = translate_tks()
    members = screen_families(fams, proteins)
    raw, parsed = load_expression()
    curves = build_curves(members, raw, parsed)
    cards = fit_window(curves)
    plot_dynamics(curves, cards)
    log("完成。")


if __name__ == "__main__":
    main()

# 参考蛋白获取（需经代理，本机直连不通 uniprot/ncbi）：
#   P=http://127.0.0.1:23333   # 或本机 git 配置的 http.proxy
#   for id in P15252 Q6T708 Q67FW6 O82803 Q84T87 W0JF90 Q8LSZ6 Q8L5G9 Q8L5B7; do
#     curl -s -x $P "https://www.ebi.ac.uk/Tools/dbfetch/dbfetch?db=uniprotkb&id=$id&format=fasta&style=raw"
#   done > data/reference_genomes/tks_rubber_pathway_queries.fasta
# （并按 FAM_REF / FAM_SRPP / FAM_CPT 前缀重写 header 第一token）
