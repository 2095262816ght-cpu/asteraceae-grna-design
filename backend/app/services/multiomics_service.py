"""方案3 组织优先指数 + 方案5 功能性脱靶危害：导出时按需计算并回填。

方案3（公式同 cs_pipeline/scripts/21，0923 修订版）：
    PriorityScore(i, t) = 0.50*Percentile(EffScore_i) - 0.25*Penalty(OffTarget_i) + 0.25*S(E_t(g))
    S(E) = 1/(1+exp(-(E-2.0)))，E = log2(TPM+1)；不可映射/缺表达 → 表达项 0（无证据即无加分）
    Penalty = min(1, (exact*1.0 + mis1*0.5 + mis2*0.2 + mis3*0.05) / 10)
口径差异（已确认）：效率百分位在**基因内**候选集上排名（同基因择优用途；scripts/21 为全候选集）。

方案5（公式同 cs_pipeline/scripts/22 轻量版）：
    Hazard_t(g) = Σ_{k ∈ 面板内命中} ω(mis_k) · w_t(gene(k))
    ω = {0: 10, 1: 3, 2: 1, 3: 0.2}；w_t = 0.1（面板基因不可映射）或 1 + 0.5*log2(TPM_t+1)
    面板 = 49 个 NLR demo 基因座 ±20kb（已确认口径）；命中 = NGG PAM 且 ≤3 错配的链特异行，
    guide 自身 on-target 行不计；n_intra_panel_sites = 面板内命中行数。
"""
import asyncio
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, GeneExpression, TargetCandidate
from backend.app.services import offtarget_service
from backend.app.services.offtarget_service import CODE_C, CODE_G, LUT, WINDOW

# 公式、权重与口径文案单点定义在 cs_pipeline.core.ranking_semantics（两轨共用）；
# 本模块只负责从数据库取数并套用公式。
from cs_pipeline.core.ranking_semantics import (
    HAZARD_OMEGA,
    HAZARD_UNMAPPABLE_WEIGHT,
    PENALTY_CAP,
    expression_term,
    hazard_gene_weight,
    penalty,
    priority_score,
    within_gene_percentiles,
)

logger = logging.getLogger(__name__)

TISSUE_ORDER = ["Root", "Stem", "Leaf", "Flower", "Seed"]
PANEL_FLANK = 20_000


def _chrom_norm(name: str) -> str:
    """Chr01/chr1 → Chr1，用于 DB 坐标与 FASTA 记录名对齐。"""
    s = str(name).strip()
    head = s[:3].lower()
    tail = s[3:]
    if tail.isdigit():
        return "Chr" + str(int(tail))
    return s if head != "chr" else "Chr" + tail


def penalty_from_profile(profile: "offtarget_service.OfftargetProfile") -> float:
    return penalty(profile.exact, profile.mis1, profile.mis2, profile.mis3)


def priority_scores_for_tpm(
    pct: float,
    profile: "offtarget_service.OfftargetProfile",
    tpm_by_tissue: Optional[Dict[str, float]],
    tissues: Sequence[str],
) -> Dict[str, float]:
    """通用入口：按 {组织: TPM} 与组织键列表求优先指数；无表达证据 → 表达项 0。

    与 priority_scores 同公式（ranking_semantics.priority_score 单点定义），组织键原样输出。
    """
    pen = penalty_from_profile(profile)
    out = {}
    for t in tissues:
        tpm = tpm_by_tissue.get(t) if tpm_by_tissue else None
        out[t] = priority_score(pct, pen, expression_term(tpm))
    return out


def priority_scores(
    pct: float,
    profile: "offtarget_service.OfftargetProfile",
    gene_expr: Optional[GeneExpression],
) -> Dict[str, float]:
    """返回 {tissue_lower: priority}。"""
    tpm_by_tissue = None
    if gene_expr is not None and gene_expr.is_mappable:
        tpm_by_tissue = {
            t.lower(): getattr(gene_expr, f"tpm_{t.lower()}") for t in TISSUE_ORDER
        }
    return priority_scores_for_tpm(pct, profile, tpm_by_tissue, [t.lower() for t in TISSUE_ORDER])


def _scan_panel_hits(
    seq20: str,
    panel_loci: Sequence[Tuple[str, str, int, int]],
    own: Tuple[str, int],
    fasta,
    fai_records,
) -> List[Tuple[str, int]]:
    """返回 [(面板基因, mis)]：面板窗口内 NGG PAM、≤3 错配的链特异行（自身 on-target 行不计）。"""
    seq20 = seq20.upper()
    p1 = LUT[np.frombuffer(seq20.encode(), dtype=np.uint8)]
    p2 = LUT[np.frombuffer(offtarget_service._revcomp(seq20).encode(), dtype=np.uint8)]
    own_gene, own_start = own
    hits: List[Tuple[str, int]] = []

    for gene_id, chrom, lo, hi in panel_loci:
        rec = fai_records.get(chrom)
        if rec is None:
            continue
        raw = offtarget_service._fetch(fasta, rec, lo, hi)
        if len(raw) < WINDOW:
            continue
        t = LUT[np.frombuffer(raw, dtype=np.uint8)]
        n = t.size - (WINDOW - 1)
        h1 = np.zeros(n, dtype=np.int16)
        h2 = np.zeros(n, dtype=np.int16)
        for k in range(WINDOW):
            h1 += t[k : k + n] != p1[k]
            h2 += t[k : k + n] != p2[k]

        w_idx = np.arange(n)
        elig1 = np.zeros(n, dtype=bool)
        ok = w_idx + 22 < t.size
        elig1[ok] = (t[w_idx[ok] + 21] == CODE_G) & (t[w_idx[ok] + 22] == CODE_G)
        elig2 = np.zeros(n, dtype=bool)
        ok2 = w_idx >= 3
        elig2[ok2] = (t[w_idx[ok2] - 3] == CODE_C) & (t[w_idx[ok2] - 2] == CODE_C)

        for h, elig in ((h1, elig1), (h2, elig2)):
            rows = np.flatnonzero(elig & (h <= 3))
            for w in rows:
                mis = int(h[w])
                if mis == 0 and gene_id == own_gene and lo + int(w) == own_start:
                    continue  # guide 自身 on-target 行不计
                hits.append((gene_id, mis))
    return hits


def hazard_scores(
    hits: List[Tuple[str, int]],
    panel_expr: Dict[str, Optional[Dict[str, float]]],
) -> Dict[str, float]:
    """返回 {tissue_lower: hazard..., 'n_intra': 行数}。"""
    out = {t.lower(): 0.0 for t in TISSUE_ORDER}
    for gene_id, mis in hits:
        w = HAZARD_OMEGA.get(mis, 0.0)
        expr = panel_expr.get(gene_id)
        for t in TISSUE_ORDER:
            if expr is None:
                factor = HAZARD_UNMAPPABLE_WEIGHT  # 面板基因不可映射
            else:
                factor = hazard_gene_weight(float(expr.get(t.lower()) or 0.0))
            out[t.lower()] += w * factor
    out["n_intra"] = float(len(hits))
    return out


async def fill_missing_multiomics(candidates, db: AsyncSession) -> int:
    """对缺多组学指标的候选按需计算并回填（脱靶分档 + 优先指数 + 面板危害）。

    幂等：已填字段跳过；基因组不可用时抛异常由调用方降级为"未计算"。
    """
    need = [
        c for c in candidates
        if c.offtarget_count_mis3 is None
        or c.priority_score_leaf is None
        or c.hazard_leaf is None
        or c.n_intra_panel_sites is None
    ]
    if not need:
        return 0

    fasta = offtarget_service.resolve_genome_fasta()

    # 1) 全基因组脱靶分档（线程池并行；基因组缺失时由其抛出并由调用方降级为"未计算"）
    profiles = await asyncio.to_thread(
        offtarget_service.compute_offtarget_profiles, [c.seq20 for c in need], fasta
    )

    # 2) 基因内效率百分位
    gene_ids = sorted({c.gene_id for c in need})
    res = await db.execute(
        select(TargetCandidate.gene_id, TargetCandidate.id, TargetCandidate.efficiency_score)
        .where(TargetCandidate.gene_id.in_(gene_ids))
    )
    pct_map = within_gene_percentiles(res.all())

    # 3) 表达证据：目标基因（优先指数）+ 面板基因（危害权重）
    panel_genes = list((await db.execute(select(Gene).where(Gene.gene_id.like("LsaT2T%")))).scalars().all())
    panel_ids = [g.gene_id for g in panel_genes]
    expr_rows = (
        await db.execute(select(GeneExpression).where(GeneExpression.gene_id.in_(set(gene_ids) | set(panel_ids))))
    ).scalars().all()
    expr_map = {e.gene_id: e for e in expr_rows}
    panel_expr: Dict[str, Optional[Dict[str, float]]] = {}
    for gid in panel_ids:
        e = expr_map.get(gid)
        panel_expr[gid] = (
            {t.lower(): float(getattr(e, f"tpm_{t.lower()}") or 0.0) for t in TISSUE_ORDER}
            if e is not None and e.is_mappable
            else None
        )
    panel_loci = [
        (g.gene_id, _chrom_norm(g.chrom), max(int(g.start) - PANEL_FLANK, 0), int(g.end) + PANEL_FLANK)
        for g in panel_genes
    ]

    # 4) 面板危害扫描（面板仅 ~2.5Mb，逐 guide 蛮力即可）
    def _hazard_all():
        fai_records = {r[0]: r for r in offtarget_service._load_fai(fasta)} if panel_loci else {}
        out = {}
        for c in need:
            key = (c.seq20.upper(), c.gene_id, int(c.start))
            hits = _scan_panel_hits(c.seq20, panel_loci, key[1:], fasta, fai_records)
            out[key] = hazard_scores(hits, panel_expr)
        return out

    hazards = await asyncio.to_thread(_hazard_all)

    # 5) 回填
    for c in need:
        p = profiles[c.seq20.upper()]
        c.offtarget_count_mis3 = p.mis3
        pct = pct_map.get(c.id)
        if pct is not None:
            scores = priority_scores(pct, p, expr_map.get(c.gene_id))
            for t in TISSUE_ORDER:
                setattr(c, f"priority_score_{t.lower()}", round(scores[t.lower()], 6))
        hz = hazards[(c.seq20.upper(), c.gene_id, int(c.start))]
        for t in TISSUE_ORDER:
            setattr(c, f"hazard_{t.lower()}", round(hz[t.lower()], 6))
        c.n_intra_panel_sites = int(hz["n_intra"])
    await db.commit()
    logger.info("多组学按需回填完成：%d 条候选", len(need))
    return len(need)
