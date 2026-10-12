"""脱靶位点详情端点（教师反馈 #1：点击脱靶数查看位点明细）。

GET /api/v1/offtarget/sites —— 全基因组扫描 20-mer（≤3 错配、PAM=NGG、正负链），
返回位点明细（坐标、链、错配数、错配位置、比对序列、CFD/MIT 评分、所在基因区域）
与 guide 级特异性汇总（CRISPOR 口径）。全基因组扫描秒级~分钟级，进程内缓存。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, TargetCandidate
from backend.app.db.session import get_db
from backend.app.services import gene_structure_service as gs_service
from backend.app.services import offtarget_service
from backend.app.services.cfd_score import aggregate_specificity
from backend.app.services.multiomics_service import fill_missing_multiomics
from backend.app.services.reference_bundle_service import resolve_bundle

router = APIRouter()

METHOD_NOTE = (
    "脱靶搜索口径：Cas-OFFinder 式全基因组扫描——20-mer 窗口 ≤3 错配、PAM=NGG、正负链分行"
    "（同一基因组位点双链均合格计两行）。位点评分：CFD（Doench 2016，错配位置×碱基对类型罚分连乘；"
    "本口径仅扫 NGG 故 PAM 罚分恒为 1）与 MIT/Hsu 2013 单位点 hit score（位置权重罚分×错配间距×错配数）。"
    "guide 级特异性沿用 CRISPOR 口径：MIT Sguide=100/(100+ΣhitScore)×100；CFD 特异性=100/Σcfd_site。"
)

RISK_BY_MM = {
    0: ("致命", "完全匹配（0 错配）脱靶：极可能被切割，最高风险"),
    1: ("高危", "1 错配脱靶：风险极高，需重点评估"),
    2: ("中", "2 错配脱靶：风险中等"),
    3: ("低", "3 错配脱靶：相对可接受"),
}


class OfftargetSiteItem(BaseModel):
    chrom: str
    start: int
    end: int
    strand: str
    protospacer20: str
    pam: str
    mismatch_count: int
    mismatch_positions: List[int]
    cfd_score: float
    mit_hit_score: float
    region_type: Optional[str] = None
    region_label: Optional[str] = None
    gene_id: Optional[str] = None
    risk_level: str
    risk_note: str
    is_ontarget: bool = False


class OfftargetSitesResponse(BaseModel):
    seq20: str
    bundle_id: str
    bundle_name: str
    genome_note: str
    profile: dict
    sites: List[OfftargetSiteItem]
    sites_truncated: bool
    specificity: dict
    method_note: str = METHOD_NOTE


def _annotate_regions(sites: List[dict], gff, db_genes_by_chrom: dict) -> None:
    """就地为每个位点补 region_type / gene_id。

    两个适配器共用 gene_structure_service 的区域判定：GFF 外显子粒度（classify_position），
    缺 GFF 时回退库内基因体/TSS 窗口近似（classify_gene_records）。
    """
    if gff is not None:
        genes = gs_service.load_gff_structure(gff)
        for s in sites:
            rtype, gid = gs_service.classify_position(genes, s["chrom"], (s["start"] + s["end"]) // 2)
            s["region_type"] = rtype
            s["region_label"] = gs_service.REGION_LABELS.get(rtype, rtype)
            s["gene_id"] = gid
        return
    for s in sites:
        rtype, rec = gs_service.classify_gene_records(
            db_genes_by_chrom, s["chrom"], (s["start"] + s["end"]) // 2
        )
        s["region_type"] = rtype
        s["region_label"] = gs_service.REGION_LABELS.get(rtype, rtype)
        s["gene_id"] = rec["gene_id"] if rec else None


@router.get("/offtarget/sites", response_model=OfftargetSitesResponse, summary="脱靶位点明细（坐标/错配/CFD/MIT/区域）")
async def get_offtarget_sites(
    seq20: str = Query(..., min_length=20, max_length=20, description="20nt gRNA 引导序列"),
    bundle_id: str = Query("lettuce", description="参考包 ID（决定扫描的参考基因组）"),
    max_sites: int = Query(200, ge=1, le=2000, description="位点明细返回上限（计数始终全量精确）"),
    ontarget_start: Optional[int] = Query(None, description="在靶位点起点（1-based，用于标记/排除自身）"),
    ontarget_end: Optional[int] = Query(None, description="在靶位点终点（1-based）"),
    db: AsyncSession = Depends(get_db),
) -> OfftargetSitesResponse:
    import asyncio

    seq20 = seq20.strip().upper()
    if any(b not in "ACGT" for b in seq20):
        raise HTTPException(status_code=400, detail="seq20 须为 20nt ACGT 序列")
    try:
        bundle = await resolve_bundle(db, bundle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if bundle.fasta is None or not bundle.fasta.exists():
        raise HTTPException(status_code=400, detail=f"参考包 {bundle.id} 无可用基因组 FASTA，无法扫描脱靶")

    try:
        profile, sites = await asyncio.to_thread(
            offtarget_service.scan_seq20, seq20, bundle.fasta, max_sites
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"脱靶扫描失败: {exc}")

    # 标记在靶：优先用调用方给的坐标，否则把首个完全匹配位点视为在靶
    ontarget_idx = None
    for i, s in enumerate(sites):
        if (
            ontarget_start is not None
            and ontarget_end is not None
            and s["start"] == ontarget_start
            and s["end"] == ontarget_end
        ):
            ontarget_idx = i
            break
    if ontarget_idx is None:
        for i, s in enumerate(sites):
            if s["mismatch_count"] == 0:
                ontarget_idx = i
                break

    # 区域注释（GFF 结构优先；lettuce 预置包退化为库内基因体/启动子近似）
    db_genes_by_chrom: dict = {}
    if bundle.gff is None or not bundle.gff.exists():
        rows = (await db.execute(select(Gene))).scalars().all()
        for g in rows:
            db_genes_by_chrom.setdefault(g.chrom, []).append(
                {"gene_id": g.gene_id, "start": int(g.start), "end": int(g.end), "strand": g.strand}
            )
        for lst in db_genes_by_chrom.values():
            lst.sort(key=lambda x: x["start"])
    _annotate_regions(sites, bundle.gff, db_genes_by_chrom)

    items: List[OfftargetSiteItem] = []
    for i, s in enumerate(sites):
        is_ot = i == ontarget_idx
        level, note = RISK_BY_MM[s["mismatch_count"]]
        if is_ot:
            level, note = "在靶", "候选 gRNA 自身的在靶位点（不计入脱靶风险汇总）"
        items.append(OfftargetSiteItem(**{**s, "risk_level": level, "risk_note": note, "is_ontarget": is_ot}))

    specificity = aggregate_specificity(seq20, sites, exclude_index=ontarget_idx)
    specificity["on_target_excluded"] = ontarget_idx is not None

    return OfftargetSitesResponse(
        seq20=seq20,
        bundle_id=bundle.id,
        bundle_name=bundle.display_name,
        genome_note=f"扫描参考基因组：{bundle.display_name}（参考包 {bundle.id}）",
        profile={
            "exact": profile.exact,
            "mis1": profile.mis1,
            "mis2": profile.mis2,
            "mis3": profile.mis3,
        },
        sites=items,
        sites_truncated=(profile.exact + profile.mis3) > len(sites),
        specificity=specificity,
    )


class ComputeOfftargetRequest(BaseModel):
    candidate_ids: List[int] = Field(..., min_length=1, max_length=500, description="候选靶点 ID 数组")


class ComputedOfftargetItem(BaseModel):
    id: int
    offtarget_count_mis3: Optional[int] = None
    n_intra_panel_sites: Optional[int] = None


class ComputeOfftargetResponse(BaseModel):
    computed: int
    items: List[ComputedOfftargetItem]


@router.post("/offtarget/compute", response_model=ComputeOfftargetResponse, summary="按需计算候选脱靶计数并回填（导出前预计算 / 表格内单条计算）")
async def compute_offtarget(
    payload: ComputeOfftargetRequest,
    db: AsyncSession = Depends(get_db),
) -> ComputeOfftargetResponse:
    """对指定候选做全基因组脱靶扫描并持久化回填（幂等：已计算的候选跳过）。

    与导出流程同口径（fill_missing_multiomics）：脱靶分档计数 + 组织优先指数 +
    功能性脱靶危害 + 面板内位点数一次算齐。单条全基因组扫描约 1 分钟，
    传多个 ID 时串行计时 ≈ 逐条累加；扫描结果进程内缓存，随后打开位点明细抽屉秒开。
    """
    rows = (
        (await db.execute(select(TargetCandidate).where(TargetCandidate.id.in_(payload.candidate_ids))))
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="指定的候选靶点在数据库中均不存在")
    try:
        computed = await fill_missing_multiomics(rows, db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"参考基因组不可用，无法计算脱靶：{exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"脱靶计算失败：{exc}")
    return ComputeOfftargetResponse(
        computed=computed,
        items=[
            ComputedOfftargetItem(
                id=c.id,
                offtarget_count_mis3=c.offtarget_count_mis3,
                n_intra_panel_sites=c.n_intra_panel_sites,
            )
            for c in sorted(rows, key=lambda x: x.id)
        ],
    )
