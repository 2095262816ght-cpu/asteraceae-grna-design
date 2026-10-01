"""Tab 2 自定义序列基因组回贴三态注释（C4 命中复用 + C5 按需脱靶 + C6 按需多组学 + D3 三档百分位）。

三态判定（seq30 为唯一输入，参考包 bundle_id 决定基因组/表达证据来源）：
1. `precomputed` — seq30 精确命中已扫描候选表 → 直接复用该 guide 的预计算多组学列
   （脱靶 mis1-3、方案3 组织优先指数、方案5 危害、表达证据），在 Tab 2 内嵌展示，不跳转；
2. `annotated`   — 未命中候选、但精确匹配参考包基因组 → 注释基因座与区域类型，
   并按需计算：C5 脱靶分档 + C6 方案3 优先指数。效率百分位三档取先可用者：
   ① 库内该基因预计算候选分布（Tab 1 直接同源）→ ② 现场枚举同基因候选 + 批量打分
   （gene_candidate_service，Tab 1 真同口径）→ ③ 贴入集合百分位（批内排名口径，须显式提供同批分）；
3. `custom`      — 未命中基因组 → 未锚定。基因内百分位/表达证据不可用，如实标注所需数据；
   若参考包基因组可用仍可按需算脱靶；有贴入集合时可算批内口径优先指数（表达项 0）。

口径纪律：缺证据即标注缺失与所需数据，绝不编造数值（unmappable 语义）。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, GeneExpression, TargetCandidate
from backend.app.services import offtarget_service, reference_bundle_service as rb_service
from backend.app.services import gene_candidate_service as gc_service
from backend.app.services import gene_structure_service as gs_service
from backend.app.services.multiomics_service import (
    TISSUE_ORDER,
    priority_scores,
    priority_scores_for_tpm,
)
from backend.app.services.reference_bundle_service import ResolvedBundle
from cs_pipeline.core.ranking_semantics import within_gene_percentiles

logger = logging.getLogger(__name__)

_seq30_index_ready = False


def _revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


async def _ensure_seq30_index(db: AsyncSession) -> None:
    global _seq30_index_ready
    if _seq30_index_ready:
        return
    try:
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_target_candidates_seq30 ON target_candidates(seq30)"))
        await db.commit()
    except Exception as exc:  # 并发建索引/无权限时忽略，退化为全表扫描
        logger.warning("seq30 索引创建失败（降级为全表扫描）: %s", exc)
    _seq30_index_ready = True


def _fetch_record(fasta: Path, rec) -> bytes:
    name, length, offset, line_bases, line_width = rec
    n_lines = (length + line_bases - 1) // line_bases
    nbytes = n_lines * line_width
    with open(fasta, "rb") as fh:
        fh.seek(offset)
        raw = fh.read(nbytes)
    return raw.replace(b"\n", b"").replace(b"\r", b"")[:length]


def find_seq30_in_genome(seq30: str, fasta: Path) -> Optional[dict]:
    """精确匹配 seq30（正链命中记 +，反向互补命中记 -），返回首个命中基因组坐标。"""
    if not fasta or not fasta.exists():
        return None
    rc = _revcomp(seq30)
    for rec in offtarget_service._load_fai(fasta):
        seq = _fetch_record(fasta, rec)
        pos = seq.find(seq30.encode())
        if pos >= 0:
            return {"chrom": rec[0], "start": pos + 1, "end": pos + 30, "strand": "+"}
        pos = seq.find(rc.encode())
        if pos >= 0:
            return {"chrom": rec[0], "start": pos + 1, "end": pos + 30, "strand": "-"}
    return None


async def _find_db_gene(db: AsyncSession, chrom: str, pos: int):
    """库内 genes 表定位（区域分类的 DB 回退适配器）：判定规则统一委托 gene_structure_service。

    返回 (region_type, record)，record 为 {gene_id, start, end, strand}；未命中为 ("intergenic", None)。
    """
    rows = (
        await db.execute(select(Gene).where(Gene.chrom.in_(gs_service.norm_chroms(chrom))))
    ).scalars().all()
    records_by_chrom: dict = {}
    for g in rows:
        records_by_chrom.setdefault(g.chrom, []).append(
            {"gene_id": g.gene_id, "start": int(g.start), "end": int(g.end), "strand": g.strand}
        )
    return gs_service.classify_gene_records(records_by_chrom, chrom, pos)


async def _load_bundle(db: AsyncSession, bundle_id: str) -> ResolvedBundle:
    """参考包解析接缝（测试可 monkeypatch）。"""
    return await rb_service.resolve_bundle(db, bundle_id)


def _paste_set_percentile(own_eff: float, peers: Sequence[float]) -> Optional[float]:
    """贴入集合百分位：own 在 同批 peers+own 上的 rank(pct=True)（批内排名口径）。"""
    rows = [("paste_set", i, float(s)) for i, s in enumerate(peers) if s is not None]
    rows.append(("paste_set", -1, float(own_eff)))
    if len(rows) < 2:
        return None
    return within_gene_percentiles(rows).get(-1)


def _compose_priority(
    bundle: ResolvedBundle, gene_id: Optional[str], pct: float, profile, dist_note: str, db_expr=None
):
    """按参考包表达布局求优先指数，返回 (scores, note)；口径标签如实。"""
    if bundle.expression_layout == "db":
        scores = priority_scores(pct, profile, db_expr)
        if db_expr is None or not db_expr.is_mappable:
            dist_note += "；该基因无同口径表达证据，表达项按 0（无证据即无加分）"
        return scores, dist_note
    if bundle.expression_layout == "tissue_tpm":
        tpm = rb_service.expression_tpm(bundle, gene_id) if gene_id else None
        scores = priority_scores_for_tpm(pct, profile, tpm, list(bundle.tissue_columns.keys()))
        if tpm is None:
            dist_note += (
                "；表达矩阵中无该基因证据（或未锚定基因），表达项按 0（无证据即无加分）"
            )
        else:
            dist_note += f"；表达证据来自参考包 {bundle.id}（组织 TPM 口径）"
        return scores, dist_note
    if bundle.expression_layout == "stage_tissue":
        # 方案3 TKS 口径（已确认：不加权、时相取峰值）：表达项(t) = sigmoid(log2(峰值TPM_t+1)−2)，
        # 组织键随参考包（根/胶乳/叶/花/花葶）；与莴苣单点 TPM 口径不可互比
        peaks = rb_service.expression_stage_peaks(bundle, gene_id) if gene_id else None
        scores = priority_scores_for_tpm(pct, profile, peaks, list(bundle.tissue_columns.keys()))
        if peaks is None:
            dist_note += "；时相矩阵中无该基因证据（或未锚定基因），表达项按 0（无证据即无加分）"
        else:
            dist_note += "；表达项取各组织 S1–S9 时相峰值 TPM（不加权、非单点 TPM，与莴苣单点 TPM 口径不可互比）"
        return scores, dist_note
    scores = priority_scores_for_tpm(pct, profile, None, [t.lower() for t in TISSUE_ORDER])
    dist_note += "；该参考包无同口径表达证据，表达项按 0（无证据即无加分）"
    return scores, dist_note


async def annotate_seq30(
    seq30: str,
    db: AsyncSession,
    bundle_id: str = "lettuce",
    efficiency_score: Optional[float] = None,
    compute_offtarget: bool = True,
    species: Optional[str] = None,
    peer_efficiency_scores: Optional[Sequence[float]] = None,
) -> dict:
    """三态注释主入口。seq30 须已通过 validate_seq30。species 为 bundle_id 的兼容别名。"""
    import asyncio

    s = seq30.strip().upper()
    seq20 = s[4:24]
    bundle = await _load_bundle(db, species or bundle_id)
    base = {
        "seq30": s,
        "seq20": seq20,
        "pam": s[24:27],
        "bundle_id": bundle.id,
        "bundle_name": bundle.display_name,
        "species": bundle.id,  # 兼容旧字段
    }

    # ---------- 状态①：命中预计算候选 → 复用多组学列（档①：库内分布同源） ----------
    await _ensure_seq30_index(db)
    cand = (
        await db.execute(select(TargetCandidate).where(TargetCandidate.seq30 == s).limit(1))
    ).scalar_one_or_none()
    if cand is not None:
        return {
            **base,
            "state": "precomputed",
            "gene_id": cand.gene_id,
            "region_type": cand.region_type,
            "annotation_note": "命中预计算候选表：以下多组学列与 Tab 1 同源同值，直接复用。",
            "hit": {"chrom": cand.chrom, "start": cand.start, "end": cand.end, "strand": cand.strand},
            "candidate": {
                "guide_id": cand.guide_id,
                "efficiency_score": cand.efficiency_score,
                "deepspcas9_score": cand.deepspcas9_score,
                "crispron_score": cand.crispron_score,
                "offtarget_count_mis3": cand.offtarget_count_mis3,
                "priority_score_leaf": cand.priority_score_leaf,
                "hazard_leaf": cand.hazard_leaf,
                "expression_status": cand.expression_status,
                "n_intra_panel_sites": cand.n_intra_panel_sites,
            },
            "offtarget": None,
            "priority_scores": None,
            "priority_note": None,
            "percentile": None,
            "percentile_basis": "库内该基因预计算候选分布（Tab 1 同源）",
            "missing_requirements": [],
        }

    # ---------- 状态②/③：基因组精确回贴 ----------
    fasta = bundle.fasta
    hit = None
    if fasta is not None:
        hit = await _to_thread_find(s, fasta)

    # C5 按需脱靶（参考包基因组；未锚定也可算——相似位点计数与精确命中无关）
    offtarget_block = None
    profile = None
    if compute_offtarget and fasta is not None:
        try:
            profile = await asyncio.to_thread(offtarget_service.profile_seq20, seq20, fasta)
            offtarget_block = {
                "exact": profile.exact,
                "mis1": profile.mis1,
                "mis2": profile.mis2,
                "mis3": profile.mis3,
            }
        except Exception as exc:
            logger.warning("按需脱靶计算失败: %s", exc)
            offtarget_block = None

    if hit is None:
        return _custom_state(base, bundle, profile, offtarget_block, efficiency_score, peer_efficiency_scores)

    # ---------- 状态②：annotated ----------
    if bundle.gene_source == "gff" and bundle.gff is not None:
        region_type, gene = gs_service.classify_gene_records(
            rb_service.load_gff_gene_index(bundle.gff), hit["chrom"], hit["start"] + 15
        )
    elif bundle.gene_source == "db":
        region_type, gene = await _find_db_gene(db, hit["chrom"], hit["start"] + 15)
    else:
        region_type, gene = None, None  # 导入包无 GFF：基因不可定位，如实不注释
    gene_id = gene["gene_id"] if gene else None
    if gene is None:
        region_type = None

    prio = None
    prio_note = None
    percentile = None
    percentile_basis = None
    if gene_id and profile is not None and efficiency_score is not None:
        pct, percentile_basis, dist_note = await _percentile_annotated(
            db, bundle, hit["chrom"], gene, s, float(efficiency_score)
        )
        if pct is not None:
            percentile = round(pct, 6)
            db_expr = None
            if bundle.expression_layout == "db":
                db_expr = (
                    await db.execute(select(GeneExpression).where(GeneExpression.gene_id == gene_id))
                ).scalar_one_or_none()
            prio, prio_note = _compose_priority(bundle, gene_id, pct, profile, dist_note, db_expr=db_expr)
        else:
            prio_note = dist_note
    elif gene_id and efficiency_score is None:
        prio_note = "未提供效率分，优先指数不计算。"
    elif not compute_offtarget and efficiency_score is not None:
        prio_note = "本次未启用按需脱靶（compute_offtarget=false），缺脱靶项，优先指数不计算。"
    elif profile is None and compute_offtarget:
        prio_note = "脱靶谱不可用（参考包基因组缺失或扫描失败），优先指数不计算。"
    elif not gene_id:
        prio_note = "未定位到基因（缺 GFF 注释或不落在基因/TSS±2kb 区间），效率百分位与表达项无定义：优先指数不计算（不硬猜）。"

    missing = []
    if bundle.expression_layout == "none" or (
        bundle.expression_layout == "tissue_tpm" and bundle.expression_path is None
    ):
        missing.append("表达矩阵（提供后表达项参与优先指数）")
    if bundle.gene_source != "db" and bundle.gff is None:
        missing.append("基因注释 GFF（提供后可定位基因与区域类型）")

    return {
        **base,
        "state": "annotated",
        "gene_id": gene_id,
        "region_type": region_type,
        "annotation_note": (
            f"精确匹配{bundle.display_name}基因组：{hit['chrom']}:{hit['start']}-{hit['end']} ({hit['strand']}链)"
            + (f"；命中基因 {gene_id}" if gene_id else "；未落在基因/TSS±2kb 区间（缺 GFF 注释则基因不可定位）")
            + "。区域类型按基因跨度/TSS±2kb 近似判定。"
        ),
        "hit": hit,
        "candidate": None,
        "offtarget": offtarget_block,
        "priority_scores": prio,
        "priority_note": prio_note,
        "percentile": percentile,
        "percentile_basis": percentile_basis,
        "missing_requirements": missing,
        "tks_expression": rb_service.stage_expression_block(bundle, gene_id)
        if (bundle.expression_layout == "stage_tissue" and gene_id)
        else None,
    }


async def _percentile_annotated(
    db: AsyncSession, bundle: ResolvedBundle, chrom: str, gene: dict, own_seq30: str, own_eff: float
):
    """效率百分位三档取先可用者，返回 (pct 或 None, 口径标签, 说明)。"""
    import asyncio

    gene_id = gene["gene_id"]
    scores_rows = (
        await db.execute(
            select(TargetCandidate.id, TargetCandidate.efficiency_score).where(
                TargetCandidate.gene_id == gene_id
            )
        )
    ).all()
    existing = [(gene_id, int(i), float(sc)) for i, sc in scores_rows if sc is not None]
    if existing:
        pct_map = within_gene_percentiles(existing + [(gene_id, -1, own_eff)])
        pct = pct_map.get(-1)
        return (
            pct,
            "库内该基因预计算候选分布（rank(pct=True) 同口径）",
            f"按需计算（方案3 公式与 Tab 1 同源）：效率百分位 {pct * 100:.1f}%"
            f"（该基因 {len(existing)} 条预计算候选分布内，rank(pct=True) 同口径）",
        )

    # 档②：现场枚举同基因候选 + 批量打分（Tab 1 真同口径）
    try:
        dist = await asyncio.to_thread(
            gc_service.gene_efficiency_distribution, bundle, chrom, gene, own_seq30, own_eff
        )
    except Exception as exc:
        logger.warning("现场候选分布构建失败: %s", exc)
        dist = None
    if dist is not None:
        dist_scores, enum_note = dist
        rows = [(gene_id, i, sc) for i, sc in enumerate(dist_scores)] + [(gene_id, -1, own_eff)]
        pct = within_gene_percentiles(rows).get(-1)
        return (
            pct,
            f"现场枚举同基因候选分布（{enum_note}，rank(pct=True) 同口径）",
            f"按需计算（方案3 公式与 Tab 1 同源）：效率百分位 {pct * 100:.1f}%"
            f"（{enum_note}，rank(pct=True) 同口径）",
        )

    return (
        None,
        None,
        "该基因在库内无预计算候选分布，且现场枚举+批量打分不可用（缺参考包基因组或模型推理不可用）："
        "效率百分位无法定义，优先指数不计算（不硬猜）。所需数据：该物种参考基因组（含 .fai）与可用模型推理。",
    )


def _custom_state(base, bundle, profile, offtarget_block, efficiency_score, peer_efficiency_scores) -> dict:
    """状态③：未锚定。缺啥写啥；有贴入集合时可算批内口径优先指数（表达项 0）。"""
    prio = None
    prio_note = None
    percentile = None
    percentile_basis = None
    if efficiency_score is not None and peer_efficiency_scores:
        pct = _paste_set_percentile(float(efficiency_score), peer_efficiency_scores)
        if pct is not None and profile is not None:
            percentile = round(pct, 6)
            percentile_basis = f"贴入集合百分位（批内排名口径，同批 {len(peer_efficiency_scores) + 1} 条，非基因内排名）"
            prio, prio_note = _compose_priority(
                bundle, None, pct, profile,
                f"按需计算（方案3 公式与 Tab 1 同源）：效率百分位 {pct * 100:.1f}%（{percentile_basis}）",
            )
        elif pct is not None:
            percentile = round(pct, 6)
            percentile_basis = f"贴入集合百分位（批内排名口径，同批 {len(peer_efficiency_scores) + 1} 条，非基因内排名）"
            prio_note = "未启用按需脱靶或参考包基因组缺失，脱靶项不可用：优先指数不计算（不硬猜）。"
        else:
            prio_note = "贴入集合内有效分数不足，百分位无法定义：优先指数不计算。"
    elif efficiency_score is not None:
        prio_note = (
            "单条无贴入集合，百分位不适用：优先指数不计算。"
            "可批量提交获得批内百分位，或导入该物种参考基因组获得基因内百分位（Tab 1 同口径）。"
        )
    else:
        prio_note = "未提供效率分，优先指数不计算。"

    missing = [
        "该物种参考基因组（精确命中后可锚定基因座、计算基因内百分位）",
        "基因注释 GFF（基因定位与区域类型）",
        "表达矩阵（优先指数表达项）",
    ]
    return {
        **base,
        "state": "custom",
        "gene_id": None,
        "region_type": None,
        "annotation_note": (
            f"该序列未精确匹配{bundle.display_name}基因组，也未命中预计算候选表："
            "无法锚定基因座，基因内百分位与表达证据不适用，不硬算。效率分等序列级结果仍然有效。"
        ),
        "hit": None,
        "candidate": None,
        "offtarget": offtarget_block,
        "priority_scores": prio,
        "priority_note": prio_note,
        "percentile": percentile,
        "percentile_basis": percentile_basis,
        "missing_requirements": missing,
    }


def find_many_seq30_in_genome(seq30s: List[str], fasta: Path) -> dict:
    """批量精确回贴：每条染色体只读一次，查全部 seq30；返回 {seq30: hit|None}。"""
    if not fasta or not fasta.exists():
        return {s: None for s in seq30s}
    pats = {s.strip().upper(): (_revcomp(s.strip().upper()), s.strip().upper()) for s in seq30s}
    out = {s: None for s in pats}
    remaining = set(pats)
    for rec in offtarget_service._load_fai(fasta):
        if not remaining:
            break
        seq = _fetch_record(fasta, rec)
        for s in list(remaining):
            rc, fwd = pats[s]
            pos = seq.find(fwd.encode())
            if pos >= 0:
                out[s] = {"chrom": rec[0], "start": pos + 1, "end": pos + 30, "strand": "+"}
                remaining.discard(s)
                continue
            pos = seq.find(rc.encode())
            if pos >= 0:
                out[s] = {"chrom": rec[0], "start": pos + 1, "end": pos + 30, "strand": "-"}
                remaining.discard(s)
    return out


async def _to_thread_find(s: str, fasta: Path) -> Optional[dict]:
    import asyncio

    return await asyncio.to_thread(find_seq30_in_genome, s, fasta)
