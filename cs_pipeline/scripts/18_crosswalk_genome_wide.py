"""18_crosswalk_genome_wide.py — 全基因组 LsT2T↔LSA crosswalk（批量定位引擎）

针对 45,981 个全基因组基因（LsT2T* 命名空间，Top100 候选 guides）批量建立与
莴苣 v1.1c (LSA) 转录组的映射，输出与 demo 金标准同构的
results/crosswalk_lsa_t2t_genome.csv + 审计报告。

与 16 号脚本的关系：
- 复用其 load_v11c_genes / resolve_lsa / GFF 路径（注释解析语义同源）；
- 定位引擎换代：16 号逐条 guide 全染色体扫描（无界精配 ~3s/条）无法 scale 到
  460 万条 guide；本脚本用 numpy 2-bit rolling code 对 v1.1c 全基因组做**一遍
  线性扫描**同时精配全部 seq20（含反向互补），耗时与 guide 数近似无关。

命中爆炸防护（实测：demo 6.2M 命中、Chr01 试点 28.7M -> 展开 660M 行 OOM）：
重复元件来源的 20-mer 命中数与共享该 code 的 guide 数双重放大，因此
  1) 扫描时按 code 全局限流 CAP_CODE 条命中（顺序前缀保留，确定性）；
  2) 投票在 **code 级**做最优命中选择（同 code 的 guide 命中集相同，最优命中
     相同），再一次性传播到 guide 行——杜绝 命中×guide 扇出展开。

tier 语义（与 CONTEXT.md ExpressionStatus 对齐）：
  tier1  同染色体共线 + 偏移一致性 >=60% + 主映射票占比 >=50%   -> mapped
  tier2  主映射明确但共线性弱/跨染色体，或串联簇票分裂        -> mapped_cluster
  tier3  主证据来自 v1.1c 未挂载 scaffold（需 >=3 票共识）      -> mapped_scaffold
  tier4  弱票作废（解析占比 <20%）或票数/簇覆盖率不足，不硬猜  -> unmappable

投票纪律与 16 号一致：每 guide 一票（contained 优先、近距离次之），弱票整体
作废标记 unmappable，**不编造映射、不硬猜**。串联簇票分裂（主映射 <50% 但
主映射+簇成员覆盖 >=50% 票）按 mapped_cluster 收录，不误杀。

运行（crispr 环境）：
    python scripts/18_crosswalk_genome_wide.py                      # 全量 Top100
    XWALK_CHROM=Chr01 python scripts/18_crosswalk_genome_wide.py    # Chr01 试点
    XWALK_GUIDES=demo/app_data.csv \
      XWALK_OUT=results/_xwalk_regress49.csv \
      XWALK_REPORT_OUT=results/_xwalk_regress49_report.md \
      XWALK_COMPARE_GOLD=results/crosswalk_lsa_t2t_0923.csv \
      python scripts/18_crosswalk_genome_wide.py                    # 49 基因金标准回归

调参加速：XWALK_VOTES_CACHE=... 落盘每 guide 投票缓存（parquet + meta），
XWALK_VOTES_IN=... 载入缓存跳过扫描，tier 规则调参秒级重跑。
"""

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyfaidx import Fasta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
V11C_FA = BASE_DIR / "data/reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa"
LETTUCE_EXPR = BASE_DIR / "data/expression/1-3_lettuce_5tissue_expression_matrix.csv"

GUIDES_CSV = Path(os.environ.get(
    "XWALK_GUIDES", str(BASE_DIR / "results/lettuce_all_genes_top100_candidates.csv")))
OUT_XWALK = Path(os.environ.get(
    "XWALK_OUT", str(BASE_DIR / "results/crosswalk_lsa_t2t_genome.csv")))
OUT_REPORT = Path(os.environ.get(
    "XWALK_REPORT_OUT", str(BASE_DIR / "results/crosswalk_lsa_t2t_genome_report.md")))
COMPARE_GOLD = os.environ.get("XWALK_COMPARE_GOLD", "")
CHROM_FILTER = os.environ.get("XWALK_CHROM", "")
VOTES_CACHE = os.environ.get("XWALK_VOTES_CACHE", "")
VOTES_IN = os.environ.get("XWALK_VOTES_IN", "")

K = 20                      # seq20 精配长度
CHUNK_BP = 20_000_000       # 基因组扫描分块
CAP_CODE = 20               # 每 code 全局命中限流（防重复元件命中爆炸）
OFFSET_TOL = 50_000         # 共线偏移一致性容差
CONSIST_MIN = 0.6           # tier1 偏移一致性门槛
VOTE_MIN = 0.5              # tier1 主映射票占比门槛
COVERAGE_MIN = 0.5          # 弱票作废线：主映射+簇成员（>=10% 票）合计占比
LOW_RESOLUTION = 0.2        # 解析占比弱票作废线（与 16 号一致）
TIER3_MIN_VOTES = 3         # scaffold 搬迁最低共识票（与 16 号一致）

TIER_NAMES = {1: "mapped", 2: "mapped_cluster", 3: "mapped_scaffold", 4: "unmappable"}


def log(msg):
    print(msg, flush=True)


def load_s16():
    """复用 16 号脚本的 v1.1c 注释解析语义（load_v11c_genes / resolve_lsa）。"""
    spec = importlib.util.spec_from_file_location(
        "xwalk16", BASE_DIR / "scripts" / "16_prep_expression_features.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_lut():
    lut = np.full(256, 4, dtype=np.uint8)
    for b in "ACGT":
        lut[ord(b)] = "ACGT".index(b)
        lut[ord(b.lower())] = "ACGT".index(b)
    return lut


def encode_rows(seqs, lut):
    """(N,) 20-mer 字符串 -> (codes uint64, valid bool)。"""
    buf = "".join(seqs).encode()
    arr = lut[np.frombuffer(buf, np.uint8).reshape(-1, K)]
    codes = np.zeros(len(arr), np.uint64)
    for k in range(K):
        codes |= arr[:, k].astype(np.uint64) << (2 * (K - 1 - k))
    valid = (arr != 4).all(axis=1)
    return codes, valid, arr


def rc_codes(arr):
    comp = (3 - arr[:, ::-1]).astype(np.uint64)
    codes = np.zeros(len(arr), np.uint64)
    for k in range(K):
        codes |= comp[:, k] << (2 * (K - 1 - k))
    return codes


def scan_sequence(seq_str, uniq_codes, lut, out):
    """单条 v1.1c 序列一遍线性扫描，命中 (pos, uniq_idx) 追加进 out。"""
    n = len(seq_str)
    for cstart in range(0, n, CHUNK_BP):
        cend = min(cstart + CHUNK_BP, n)
        frag = seq_str[cstart:cend + K - 1]
        arr = lut[np.frombuffer(frag.encode(), np.uint8)]
        w = len(arr) - K + 1
        if w <= 0:
            continue
        codes = np.zeros(w, np.uint64)
        arr64 = arr.astype(np.uint64)
        for k in range(K):
            codes |= arr64[k:k + w] << (2 * (K - 1 - k))

        bad = arr == 4
        if bad.any():
            cs = np.zeros(len(arr) + 1, np.int32)
            np.cumsum(bad.astype(np.int32), out=cs[1:])
            valid = (cs[K:] - cs[:-K]) == 0
            vcodes = codes[valid]
            vpos = np.nonzero(valid)[0] + cstart
        else:
            vcodes = codes
            vpos = np.arange(cstart, cstart + w, dtype=np.int64)

        idx = np.searchsorted(uniq_codes, vcodes)
        idxc = np.clip(idx, 0, len(uniq_codes) - 1)
        m = uniq_codes[idxc] == vcodes
        if m.any():
            out.append((vpos[m], idxc[m]))


def chrom_num(c):
    s = str(c).replace("Chr", "").lstrip("0")
    return int(s) if s.isdigit() else None


def cap_code_stream(pos, u, code_counts):
    """序列内命中按 code 全局限流 CAP_CODE（前缀保留，确定性）。

    同一 code 在本序列内的出现按位置序编号 occ；全局已保留 prior 条，
    本条保留当且仅当 prior + occ < CAP_CODE。返回 (kept_pos, kept_u)。
    """
    if len(u) == 0:
        return pos, u
    order = np.argsort(u, kind="stable")
    u_s = u[order]
    p_s = pos[order]
    uniq_u, starts_u, cnt_u = np.unique(u_s, return_index=True, return_counts=True)
    occ = np.arange(len(u_s)) - np.repeat(starts_u, cnt_u)
    prior_u = code_counts[uniq_u]
    keep_cnt = np.clip(CAP_CODE - prior_u, 0, cnt_u)
    code_counts[uniq_u] = prior_u + keep_cnt
    keep = occ < np.repeat(keep_cnt, cnt_u)
    return p_s[keep], u_s[keep]


def build_votes_code_level(matches, v11c_keys, idx16, guide_rows_flat, bstarts,
                           uniq_codes, gnum_arr, gstart_arr):
    """code 级最优命中 -> 传播至 guide 行 -> 每 guide 一票。

    同 code 的 guide 命中集相同，最优命中（contained 优先、dist 次之、pos 兜底）
    也相同，因此在 code 级做一次选择即可，杜绝 命中×guide 扇出。
    """
    seq_of = np.asarray(v11c_keys, dtype=object)
    log(f"    解析 {len(matches[0]):,} 条限流命中至 LSA")
    recs = []
    for seq_id, pos, u in zip(*matches):
        key = seq_of[seq_id]
        lsa, dist, how = idx16["resolve"](idx16["idx"], key, int(pos))
        if lsa is None:
            continue
        recs.append((int(u), lsa, how, float(dist), int(pos), int(seq_id)))
    if not recs:
        return pd.DataFrame(columns=[
            "row", "gene_id", "lsa", "how", "how_rank", "dist", "pos",
            "seq_key", "is_scaffold", "collinear", "offset"])
    mdf = pd.DataFrame(recs, columns=["u", "lsa", "how", "dist", "pos", "seq_id"])
    mdf["how_rank"] = (mdf["how"] != "contained").astype(int)
    mdf = mdf.sort_values(["u", "how_rank", "dist", "pos"], kind="stable")
    best = mdf.drop_duplicates("u", keep="first")
    log(f"    code 级最优命中 {len(best):,} / {len(uniq_codes):,} codes")

    lengths = bstarts[best["u"].values + 1] - bstarts[best["u"].values]
    rep_u = np.repeat(best["u"].values, lengths)
    seg = np.zeros(len(best), np.int64)
    np.cumsum(lengths[:-1], out=seg[1:])
    within = np.arange(int(lengths.sum()), dtype=np.int64) - np.repeat(seg, lengths)
    rows = guide_rows_flat[bstarts[rep_u] + within]

    rep_lsa = np.repeat(best["lsa"].values, lengths)
    rep_how = np.repeat(best["how"].values, lengths)
    rep_rank = np.repeat(best["how_rank"].values, lengths)
    rep_dist = np.repeat(best["dist"].values, lengths)
    rep_pos = np.repeat(best["pos"].values, lengths)
    rep_seq = np.repeat(best["seq_id"].values, lengths)

    gv = pd.DataFrame({
        "row": rows, "lsa": rep_lsa, "how": rep_how, "how_rank": rep_rank,
        "dist": rep_dist, "pos": rep_pos, "seq_id": rep_seq,
    })
    gv = gv.sort_values(["row", "how_rank", "dist", "pos"], kind="stable")
    gv = gv.drop_duplicates("row", keep="first").reset_index(drop=True)

    gv["seq_key"] = [seq_of[s] for s in gv["seq_id"].values]
    gv["is_scaffold"] = ~gv["seq_key"].astype(str).str.startswith("Chr")
    gnum = pd.to_numeric(pd.Series(gnum_arr), errors="coerce").values
    gstart = gstart_arr[gv["row"].values]
    hit_num = pd.to_numeric(gv["seq_key"].map(chrom_num), errors="coerce").values
    gv["collinear"] = (gnum[gv["row"].values] == hit_num)  # NaN != NaN -> False
    gv["offset"] = gv["pos"].values - gstart
    return gv


def aggregate(gv, n_guides_per_gene, gene_chrom, expr_ids):
    rows = []
    by_gene = {g: sub for g, sub in gv.groupby("gene_id")} if len(gv) else {}
    for gid, n_guides in n_guides_per_gene.items():
        sub = by_gene.get(gid)
        n = gene_chrom.get(gid)
        chrom_delivered = ("Chr%02d" % int(n)) if n is not None and not pd.isna(n) else None
        if sub is None or len(sub) == 0:
            rows.append({
                "gene_id": gid, "chrom_delivered": chrom_delivered,
                "n_guides": int(n_guides), "tier": 4,
                "lsa_primary": None, "lsa_primary_mode": None,
                "lsa_vote_frac": 0.0, "lsa_resolved_frac": 0.0,
                "lsa_cluster": None, "n_cluster": 0,
                "scaffold_evidence": None, "voided_low_resolution": True,
                "offset_consistency": 0.0, "cluster_coverage": 0.0,
                "in_expression_matrix": False,
            })
            continue

        n_res = len(sub)
        resolved_frac = n_res / max(int(n_guides), 1)
        voided = resolved_frac < LOW_RESOLUTION
        lsa_votes = sub["lsa"].value_counts()
        primary = str(lsa_votes.index[0])
        top_votes = int(lsa_votes.iloc[0])
        vote_frac = top_votes / max(n_res, 1)
        cluster = [f"{l}:{int(v)}" for l, v in lsa_votes.items()
                   if v >= 0.1 * n_res]
        coverage = sum(int(v) for _, v in lsa_votes.items() if v >= 0.1 * n_res) / max(n_res, 1)

        p_rows = sub[sub["lsa"] == primary]
        mode = str(p_rows["how"].value_counts().index[0])
        scaf = p_rows[p_rows["is_scaffold"]]["seq_key"].value_counts()
        scaffold_ev = ";".join(list(scaf.index[:2])) if len(scaf) else None
        scaffold_frac = len(p_rows[p_rows["is_scaffold"]]) / max(len(p_rows), 1)

        off = sub.loc[sub["collinear"], "offset"]
        if len(off) >= 3:
            med = float(np.median(off))
            consistency = float((np.abs(off - med) <= OFFSET_TOL).mean())
        else:
            consistency = 0.0

        if voided or n_res < TIER3_MIN_VOTES or coverage < COVERAGE_MIN:
            tier = 4
        elif scaffold_frac > 0.5 and int(scaf.sum()) >= TIER3_MIN_VOTES:
            tier = 3
        elif consistency >= CONSIST_MIN and vote_frac >= VOTE_MIN:
            tier = 1
        else:
            tier = 2

        rows.append({
            "gene_id": gid, "chrom_delivered": chrom_delivered,
            "n_guides": int(n_guides), "tier": tier,
            "lsa_primary": None if tier == 4 else primary,
            "lsa_primary_mode": None if tier == 4 else mode,
            "lsa_vote_frac": round(vote_frac, 3),
            "lsa_resolved_frac": round(resolved_frac, 3),
            "lsa_cluster": ";".join(cluster) if tier != 4 else None,
            "n_cluster": len(cluster) if tier != 4 else 0,
            "scaffold_evidence": scaffold_ev if tier != 4 else None,
            "voided_low_resolution": bool(voided),
            "offset_consistency": round(consistency, 3),
            "cluster_coverage": round(coverage, 3),
            "in_expression_matrix": bool(tier != 4 and primary in expr_ids),
        })
    return pd.DataFrame(rows)


def write_report(df, guides_info, gold_diff=None):
    lines = [
        "# 全基因组 LSA↔T2T crosswalk 审计报告",
        "",
        f"> 生成脚本：`scripts/18_crosswalk_genome_wide.py`（批量定位引擎）",
        f"> guides 来源：`{guides_info}`",
        f"> 基因数：{len(df)}，guide 解析占比均值：{df.lsa_resolved_frac.mean():.1%}",
        "",
        "## tier 分布",
        "",
        "| tier | 语义 | 基因数 | 占比 |",
        "|---|---|---|---|",
    ]
    vc = df["tier"].value_counts().sort_index()
    for t, n in vc.items():
        lines.append(f"| {t} | {TIER_NAMES[int(t)]} | {n} | {n / len(df):.1%} |")

    mapped = df[df["tier"] <= 3]
    lines += [
        "",
        "## 映射质量",
        "",
        f"- 可映射基因（tier1-3）：{len(mapped)}（{len(mapped) / len(df):.1%}）",
        f"- 其中收录于 5 组织表达矩阵：{int(df.in_expression_matrix.sum())}",
        f"- 主映射票占比均值：{mapped.lsa_vote_frac.mean():.1%}" if len(mapped) else "-（无可映射基因）",
        f"- 串联簇（n_cluster>1）：{int((mapped.n_cluster > 1).sum())}" if len(mapped) else "",
        f"- scaffold 搬迁（tier3）：{int((df.tier == 3).sum())}",
        "",
        "## 不可映射（tier4）样例",
        "",
        "| 基因 | 解析占比 | 票占比 | 簇覆盖 | 弱票作废 |",
        "|---|---|---|---|---|",
    ]
    for _, r in df[df["tier"] == 4].head(10).iterrows():
        lines.append(f"| `{r.gene_id}` | {r.lsa_resolved_frac:.1%} | "
                     f"{r.lsa_vote_frac:.1%} | {r.cluster_coverage:.1%} | "
                     f"{r.voided_low_resolution} |")

    if gold_diff is not None:
        lines += ["", "## 金标准回归（49 个 demo NLR 基因）", ""]
        lines += gold_diff
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    log(f"[8] 审计报告 -> {OUT_REPORT}")


def compare_gold(df):
    gold = pd.read_csv(COMPARE_GOLD)
    m = gold.merge(df, on="gene_id", suffixes=("_gold", "_new"))
    both_map = m[(m["tier_gold"] <= 3) & (m["tier_new"] <= 3)]

    def gold_members(r):
        members = {str(r["lsa_primary_gold"])}
        if pd.notna(r["lsa_cluster_gold"]):
            members.update(p.split(":")[0] for p in str(r["lsa_cluster_gold"]).split(";"))
        return members

    agree_primary = (both_map["lsa_primary_gold"] == both_map["lsa_primary_new"]).sum()
    same_locus = sum(
        str(r["lsa_primary_new"]) in gold_members(r) for _, r in both_map.iterrows())
    state_agree = ((m["tier_gold"] == 4) == (m["tier_new"] == 4)).sum()
    conf = pd.crosstab(m["tier_gold"], m["tier_new"])
    state_mismatch = (m["tier_gold"] == 4) != (m["tier_new"] == 4)
    primary_mismatch = ((m["tier_gold"] <= 3) & (m["tier_new"] <= 3)
                        & (m["lsa_primary_gold"] != m["lsa_primary_new"]))
    diff = m[state_mismatch | primary_mismatch]
    diff_path = OUT_XWALK.with_name(OUT_XWALK.stem + "_regress_diff.csv")
    diff[["gene_id", "tier_gold", "lsa_primary_gold", "tier_new",
          "lsa_primary_new", "lsa_vote_frac_new", "lsa_resolved_frac_new"]].to_csv(
        diff_path, index=False)
    lines = [
        f"- 双方可映射基因：{len(both_map)}，lsa_primary 完全一致：{agree_primary}"
        f"（{agree_primary / max(len(both_map), 1):.1%}），同位点一致"
        f"（含串联簇内成员互换）：{same_locus}（{same_locus / max(len(both_map), 1):.1%}）",
        f"- 映射状态（可映射/不可映射）一致：{state_agree}/{len(m)}"
        f"（{state_agree / max(len(m), 1):.1%}）",
        f"- 不一致明细：`{diff_path.name}`",
        "",
        "tier 混淆矩阵（行=金标准，列=新引擎）：", "",
        "```", conf.to_string(), "```",
    ]
    log(f"[回归] lsa_primary 一致 {agree_primary}/{len(both_map)}（同位点 {same_locus}），"
        f"状态一致 {state_agree}/{len(m)}，明细 -> {diff_path.name}")
    return lines


def run_locate_and_vote():
    s16 = load_s16()
    idx16 = {"idx": s16.load_v11c_genes(), "resolve": s16.resolve_lsa}
    lut = build_lut()

    log(f"[1] 加载 guides: {GUIDES_CSV}")
    gdf = pd.read_csv(GUIDES_CSV,
                      usecols=["guide_id", "gene_id", "chrom", "start", "seq20"])
    gdf["seq20"] = gdf["seq20"].str.upper()
    gdf["g_chrom_num"] = gdf["chrom"].map(chrom_num)
    if CHROM_FILTER:
        want = chrom_num(CHROM_FILTER)
        gdf = gdf[gdf["g_chrom_num"] == want]
        log(f"    XWALK_CHROM={CHROM_FILTER} 试点：{len(gdf)} guides / "
            f"{gdf.gene_id.nunique()} 基因")
    gdf = gdf.reset_index(drop=True)
    gdf["row"] = np.arange(len(gdf), dtype=np.int64)
    n_guides_per_gene = gdf.groupby("gene_id").size()
    gene_chrom = gdf.groupby("gene_id")["g_chrom_num"].first().to_dict()
    log(f"    共 {len(gdf):,} guides / {len(n_guides_per_gene):,} 基因")

    log("[2] 构建 20-mer 模式集（seq20 + 反向互补）")
    codes_f, valid_f, arr_f = encode_rows(gdf["seq20"].tolist(), lut)
    codes_rc = rc_codes(arr_f)
    all_codes = np.concatenate([codes_f[valid_f], codes_rc[valid_f]])
    all_rows = np.concatenate([gdf["row"].values[valid_f],
                               gdf["row"].values[valid_f]])
    uniq_codes, inv = np.unique(all_codes, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    guide_rows_flat = all_rows[order]
    bstarts = np.zeros(len(uniq_codes) + 1, np.int64)
    np.cumsum(np.bincount(inv, minlength=len(uniq_codes)), out=bstarts[1:])
    log(f"    唯一 20-mer code {len(uniq_codes):,}（有效 guide "
        f"{int(valid_f.sum()):,}/{len(gdf):,}）")

    log(f"[3] 扫描 v1.1c 全基因组（一遍线性，code 级限流 {CAP_CODE}/code）")
    v11c = Fasta(str(V11C_FA))
    v11c_keys = list(v11c.keys())
    code_counts = np.zeros(len(uniq_codes), np.int32)
    kept_pos, kept_u, kept_seq = [], [], []
    n_raw = 0
    for i, key in enumerate(v11c_keys):
        per_seq = []
        scan_sequence(str(v11c[key][:]).upper(), uniq_codes, lut, per_seq)
        if per_seq:
            p = np.concatenate([x[0] for x in per_seq])
            u = np.concatenate([x[1] for x in per_seq])
            n_raw += len(p)
            kp, ku = cap_code_stream(p, u, code_counts)
            if len(ku):
                kept_pos.append(kp)
                kept_u.append(ku)
                kept_seq.append(np.full(len(ku), i, np.int32))
        if (i + 1) % 20 == 0 or i + 1 == len(v11c_keys):
            log(f"    已扫 {i + 1}/{len(v11c_keys)} 条序列，原始命中 {n_raw:,}，"
                f"限流后 {sum(len(x) for x in kept_u):,}")
    matches = (np.concatenate(kept_seq), np.concatenate(kept_pos), np.concatenate(kept_u))
    log(f"[4] 原始命中 {n_raw:,} -> 限流后 {len(matches[0]):,}（{CAP_CODE}/code）")

    gnum_arr = gdf["g_chrom_num"].values.astype(object)
    gstart_arr = gdf["start"].values.astype(np.int64)
    gv = build_votes_code_level(
        matches, v11c_keys, idx16, guide_rows_flat, bstarts,
        uniq_codes, gnum_arr, gstart_arr)
    gv = gv.merge(gdf[["row", "gene_id"]], on="row")
    log(f"[5] 有效票 {len(gv):,} / {len(gdf):,} guides")

    meta = pd.DataFrame({
        "gene_id": n_guides_per_gene.index,
        "n_guides": n_guides_per_gene.values,
        "g_chrom_num": [gene_chrom[g] for g in n_guides_per_gene.index],
    })
    if VOTES_CACHE:
        gv.to_parquet(VOTES_CACHE, index=False)
        meta.to_parquet(VOTES_CACHE + ".meta.parquet", index=False)
        log(f"    投票缓存 -> {VOTES_CACHE}")
    return gv, meta


def main():
    if VOTES_IN:
        gv = pd.read_parquet(VOTES_IN)
        meta = pd.read_parquet(VOTES_IN + ".meta.parquet").set_index("gene_id")
        log(f"[缓存] 载入投票缓存 {VOTES_IN}: {len(gv):,} 票 / {len(meta):,} 基因")
    else:
        gv, meta = run_locate_and_vote()
        meta = meta.set_index("gene_id")

    n_guides_per_gene = meta["n_guides"]
    gene_chrom = meta["g_chrom_num"].to_dict()

    # 目录补全：无候选 guide 的基因也输出 tier4 行，保证 crosswalk 覆盖全目录
    catalog_file = BASE_DIR / "results" / "lettuce_all_genes_catalog.csv"
    if catalog_file.exists() and not CHROM_FILTER and not COMPARE_GOLD:
        catalog = pd.read_csv(catalog_file, usecols=["gene_id", "g_chrom_norm"])
        catalog["gene_id"] = catalog["gene_id"].astype(str)
        known = set(n_guides_per_gene.index)
        missing = catalog[~catalog["gene_id"].isin(known)]
        if len(missing):
            log(f"[6a] 目录补全：{len(missing)} 个无候选 guide 基因补 tier4 行")
            n_guides_per_gene = pd.concat([
                n_guides_per_gene,
                pd.Series(0, index=missing["gene_id"].tolist(), dtype=n_guides_per_gene.dtype),
            ])
            for g, c in zip(missing["gene_id"], missing["g_chrom_norm"]):
                gene_chrom[g] = chrom_num(c)

    log("[6] 基因级聚合与 tier 判定")
    expr_ids = set()
    if LETTUCE_EXPR.exists():
        expr_ids = set(pd.read_csv(LETTUCE_EXPR, usecols=["GeneID"])["GeneID"])
    df = aggregate(gv, n_guides_per_gene, gene_chrom, expr_ids)

    log(f"[7] 输出 {len(df):,} 行 -> {OUT_XWALK}")
    df = df.sort_values("gene_id").reset_index(drop=True)
    df.to_csv(OUT_XWALK, index=False)

    gold_diff = compare_gold(df) if COMPARE_GOLD else None
    write_report(df, GUIDES_CSV.name, gold_diff)
    log("\n完成。")


if __name__ == "__main__":
    main()
