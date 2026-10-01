from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, TargetCandidate, GeneExpression
from backend.app.db.session import get_db
from backend.app.services.expression_evidence import derive_expression_evidence
from backend.app.services.expression_fitness_service import expression_fitness

router = APIRouter()

TISSUES = {"Root": "根", "Stem": "茎", "Leaf": "叶", "Flower": "花", "Seed": "种子"}
VALID_TISSUES = {"Root", "Stem", "Leaf", "Flower", "Seed"}


class GeneResponse(BaseModel):
    gene_id: str
    chrom: str
    start: int
    end: int
    strand: str
    nlr_type: Optional[str] = None
    candidate_count: int

    model_config = {"from_attributes": True}


class GeneExpressionResponse(BaseModel):
    gene_id: str
    lsa_id: Optional[str] = None
    tier: Optional[int] = None
    lsa_vote_frac: Optional[float] = None
    lsa_resolved_frac: Optional[float] = None
    is_mappable: bool
    unmappable_reason: Optional[str] = None
    tpm_root: Optional[float] = None
    tpm_stem: Optional[float] = None
    tpm_leaf: Optional[float] = None
    tpm_flower: Optional[float] = None
    tpm_seed: Optional[float] = None
    top_tissue: Optional[str] = None
    top_tpm: Optional[float] = None
    tau: Optional[float] = None
    n_cluster: int = 1
    lsa_cluster: Optional[str] = None
    scaffold_evidence: Optional[str] = None
    tpm_dict: Dict[str, float] = {}

    model_config = {"from_attributes": True}


class CandidateItem(BaseModel):
    id: int
    guide_id: str
    gene_id: str
    chrom: str
    start: int
    end: int
    strand: str
    seq30: str
    seq20: str
    pam: str
    region_type: str
    is_centromere: bool
    is_exon: bool
    gc_pct: float
    tm_c: float
    offtarget_count_mis3: Optional[int] = None
    deepspcas9_score: Optional[float] = None
    crispron_score: Optional[float] = None
    efficiency_score: Optional[float] = None

    # 表达适配度（教师反馈 #2）：poly-T 硬过滤后列表内 poly_t 恒为 False；MFE 为 spacer-only 口径
    poly_t: bool = False
    five_prime_g: bool = False
    mfe_kcal: Optional[float] = None
    mfe_risk: Optional[bool] = None
    expression_fitness_note: Optional[str] = None

    # 多组学与方案3/方案5组织特异性字段
    priority_score: Optional[float] = None
    hazard_score: Optional[float] = None
    expression_status: Optional[str] = None
    expression_status_display: Optional[str] = None
    expression_evidence_note: Optional[str] = None
    n_intra_panel_sites: Optional[int] = None
    target_tissue: Optional[str] = "Leaf"

    model_config = {"from_attributes": True}



class GeneSummary(BaseModel):
    gene_id: str
    chrom: str
    start: int
    end: int
    strand: str
    total_candidates: int
    filtered_candidates: int
    poly_t_filtered_count: int = 0


class CandidatesResponse(BaseModel):
    items: List[CandidateItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    gene_summary: Optional[GeneSummary] = None


@router.get("/genes", response_model=List[GeneResponse], summary="获取基因元数据（支持关键字搜索与限量）")
async def list_genes(
    q: Optional[str] = Query(None, description="搜索关键字，模糊匹配基因 ID / 染色体 / 类型"),
    limit: Optional[int] = Query(None, ge=1, le=60000, description="返回条数上限（缺省返回全部）"),
    db: AsyncSession = Depends(get_db),
) -> List[GeneResponse]:
    stmt = select(Gene)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Gene.gene_id.like(like),
                Gene.chrom.like(like),
                Gene.nlr_type.like(like),
            )
        )
    stmt = stmt.order_by(Gene.gene_id)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/genes/{gene_id}/expression", response_model=GeneExpressionResponse, summary="获取指定基因的多组织表达图谱与 crosswalk 映射元数据")
async def get_gene_expression(
    gene_id: str,
    db: AsyncSession = Depends(get_db),
) -> GeneExpressionResponse:
    stmt = select(GeneExpression).where(GeneExpression.gene_id == gene_id)
    res = await db.execute(stmt)
    expr = res.scalar_one_or_none()

    if not expr:
        return GeneExpressionResponse(
            gene_id=gene_id,
            is_mappable=False,
            unmappable_reason=f"未找到基因 {gene_id} 的 crosswalk 映射或表达图谱记录。",
        )

    tpm_dict = {}
    if expr.is_mappable:
        tpm_dict = {
            "Root": expr.tpm_root or 0.0,
            "Stem": expr.tpm_stem or 0.0,
            "Leaf": expr.tpm_leaf or 0.0,
            "Flower": expr.tpm_flower or 0.0,
            "Seed": expr.tpm_seed or 0.0,
        }

    return GeneExpressionResponse(
        gene_id=expr.gene_id,
        lsa_id=expr.lsa_id,
        tier=expr.tier,
        lsa_vote_frac=expr.lsa_vote_frac,
        lsa_resolved_frac=expr.lsa_resolved_frac,
        is_mappable=expr.is_mappable,
        unmappable_reason=expr.unmappable_reason,
        tpm_root=expr.tpm_root,
        tpm_stem=expr.tpm_stem,
        tpm_leaf=expr.tpm_leaf,
        tpm_flower=expr.tpm_flower,
        tpm_seed=expr.tpm_seed,
        top_tissue=expr.top_tissue,
        top_tpm=expr.top_tpm,
        tau=expr.tau,
        n_cluster=expr.n_cluster or 1,
        lsa_cluster=expr.lsa_cluster,
        scaffold_evidence=expr.scaffold_evidence,
        tpm_dict=tpm_dict,
    )


@router.get("/candidates", response_model=CandidatesResponse, summary="多条件复合过滤候选 gRNA 靶点")
async def query_candidates(
    gene_id: str = Query(..., description="目标靶基因 ID，例如 LsaT2T01G023690"),
    target_tissue: str = Query("Leaf", description="目标组织：Root | Stem | Leaf | Flower | Seed"),
    min_score: Optional[float] = Query(None, description="最低预测效率分"),
    exclude_centromere: bool = Query(False, description="是否过滤掉着丝粒不稳定区靶点"),
    exon_only: bool = Query(False, description="是否仅保留外显子/编码区靶点"),
    region_type: Optional[str] = Query(None, description="功能元件过滤：exon | promoter | all"),
    page: int = Query(1, ge=1, description="当前分页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页记录数"),
    sort_by: str = Query("efficiency_score", description="排序字段：efficiency_score, priority_score, start, offtarget_count_mis3, gc_pct"),
    sort_order: str = Query("desc", description="排序方向：desc | asc"),
    db: AsyncSession = Depends(get_db),
) -> CandidatesResponse:
    # 规范化目标组织名称
    norm_tissue = target_tissue.capitalize()
    if norm_tissue not in VALID_TISSUES:
        norm_tissue = "Leaf"
    tissue_lower = norm_tissue.lower()

    # 1. 验证基因是否存在
    gene_stmt = select(Gene).where(Gene.gene_id == gene_id)
    gene_res = await db.execute(gene_stmt)
    gene = gene_res.scalar_one_or_none()
    if not gene:
        gene_summary = None
    else:
        gene_summary = GeneSummary(
            gene_id=gene.gene_id,
            chrom=gene.chrom,
            start=gene.start,
            end=gene.end,
            strand=gene.strand,
            total_candidates=gene.candidate_count,
            filtered_candidates=0,
        )

    # 2. 构造查询条件
    if region_type and region_type.lower() == "none":
        return CandidatesResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=1,
            gene_summary=gene_summary,
        )

    stmt = select(TargetCandidate).where(TargetCandidate.gene_id == gene_id)

    # poly-T 硬过滤（教师反馈 #2）：U6 转录遇 TTTT 提前终止，含 TTTT 的候选不参与列表
    poly_t_stmt = select(func.count()).where(
        TargetCandidate.gene_id == gene_id,
        TargetCandidate.seq20.like("%TTTT%"),
    )
    poly_t_filtered_count = (await db.execute(poly_t_stmt)).scalar() or 0
    stmt = stmt.where(TargetCandidate.seq20.notlike("%TTTT%"))

    if min_score is not None:
        stmt = stmt.where(TargetCandidate.efficiency_score >= min_score)
    if exclude_centromere:
        stmt = stmt.where(TargetCandidate.is_centromere == False)
    if region_type and region_type.lower() in ("exon", "promoter"):
        stmt = stmt.where(TargetCandidate.region_type == region_type.lower())
    elif exon_only:
        stmt = stmt.where(TargetCandidate.is_exon == True)

    # 3. 统计总匹配数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    if gene_summary:
        gene_summary.filtered_candidates = total_count
        gene_summary.poly_t_filtered_count = poly_t_filtered_count

    # 4. 排序处理（支持根据目标组织进行方案3组织优先指数或方案5脱靶危害排序）
    if sort_by in ("priority_score", f"priority_score_{tissue_lower}"):
        sort_col = getattr(TargetCandidate, f"priority_score_{tissue_lower}", TargetCandidate.efficiency_score)
    elif sort_by in ("hazard_score", f"hazard_{tissue_lower}"):
        sort_col = getattr(TargetCandidate, f"hazard_{tissue_lower}", TargetCandidate.offtarget_count_mis3)
    else:
        sort_col = getattr(TargetCandidate, sort_by, TargetCandidate.efficiency_score)

    if sort_order.lower() == "asc":
        stmt = stmt.order_by(asc(sort_col).nulls_last())
    else:
        stmt = stmt.order_by(desc(sort_col).nulls_last())

    # 5. 分页执行
    offset_val = (page - 1) * page_size
    stmt = stmt.offset(offset_val).limit(page_size)

    items_res = await db.execute(stmt)
    raw_items = list(items_res.scalars().all())

    # 基因级表达证据（候选级 expression_status 缺失时派生状态与说明）
    expr_res = await db.execute(select(GeneExpression).where(GeneExpression.gene_id == gene_id))
    gene_expr = expr_res.scalar_one_or_none()

    # 6. 构造 CandidateItem 响应列表（绑定当前所选目标组织的多组学指标）
    items = []
    for c in raw_items:
        prio = getattr(c, f"priority_score_{tissue_lower}", None)
        haz = getattr(c, f"hazard_{tissue_lower}", None)
        expr_status, expr_display, expr_note = derive_expression_evidence(c.expression_status, gene_expr)
        fit = expression_fitness(c.seq20)

        items.append(
            CandidateItem(
                id=c.id,
                guide_id=c.guide_id,
                gene_id=c.gene_id,
                chrom=c.chrom,
                start=c.start,
                end=c.end,
                strand=c.strand,
                seq30=c.seq30,
                seq20=c.seq20,
                pam=c.pam,
                region_type=c.region_type,
                is_centromere=c.is_centromere,
                is_exon=c.is_exon,
                gc_pct=c.gc_pct,
                tm_c=c.tm_c,
                offtarget_count_mis3=c.offtarget_count_mis3,
                deepspcas9_score=c.deepspcas9_score,
                crispron_score=c.crispron_score,
                efficiency_score=c.efficiency_score,
                poly_t=fit["poly_t"],
                five_prime_g=fit["five_prime_g"],
                mfe_kcal=fit["mfe_kcal"],
                mfe_risk=fit["mfe_risk"],
                expression_fitness_note=fit["note"],
                priority_score=prio,
                hazard_score=haz,
                expression_status=expr_status,
                expression_status_display=expr_display,
                expression_evidence_note=expr_note,
                n_intra_panel_sites=c.n_intra_panel_sites,
                target_tissue=norm_tissue,
            )
        )

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return CandidatesResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        gene_summary=gene_summary,
    )

