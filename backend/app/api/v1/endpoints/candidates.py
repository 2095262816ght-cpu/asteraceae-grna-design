from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Gene, TargetCandidate
from backend.app.db.session import get_db

router = APIRouter()


class GeneResponse(BaseModel):
    gene_id: str
    chrom: str
    start: int
    end: int
    strand: str
    nlr_type: Optional[str] = None
    candidate_count: int

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
    offtarget_count_mis3: int
    deepspcas9_score: Optional[float] = None
    crispron_score: Optional[float] = None
    efficiency_score: Optional[float] = None

    model_config = {"from_attributes": True}



class GeneSummary(BaseModel):
    gene_id: str
    chrom: str
    start: int
    end: int
    strand: str
    total_candidates: int
    filtered_candidates: int


class CandidatesResponse(BaseModel):
    items: List[CandidateItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    gene_summary: Optional[GeneSummary] = None


@router.get("/genes", response_model=List[GeneResponse], summary="获取所有代表基因元数据")
async def list_genes(
    db: AsyncSession = Depends(get_db),
) -> List[GeneResponse]:
    stmt = select(Gene).order_by(Gene.gene_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/candidates", response_model=CandidatesResponse, summary="多条件复合过滤候选 gRNA 靶点")
async def query_candidates(
    gene_id: str = Query(..., description="目标靶基因 ID，例如 LsaT2T01G023690"),
    min_score: Optional[float] = Query(None, description="最低预测效率分"),
    exclude_centromere: bool = Query(False, description="是否过滤掉着丝粒不稳定区靶点"),
    exon_only: bool = Query(False, description="是否仅保留外显子/编码区靶点"),
    page: int = Query(1, ge=1, description="当前分页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页记录数"),
    sort_by: str = Query("efficiency_score", description="排序字段：efficiency_score, start, offtarget_count_mis3, gc_pct"),
    sort_order: str = Query("desc", description="排序方向：desc | asc"),
    db: AsyncSession = Depends(get_db),
) -> CandidatesResponse:
    # 1. 验证基因是否存在
    gene_stmt = select(Gene).where(Gene.gene_id == gene_id)
    gene_res = await db.execute(gene_stmt)
    gene = gene_res.scalar_one_or_none()
    if not gene:
        # 如果基因表未显式查到，提供兜底汇总
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
    stmt = select(TargetCandidate).where(TargetCandidate.gene_id == gene_id)

    if min_score is not None:
        stmt = stmt.where(TargetCandidate.efficiency_score >= min_score)
    if exclude_centromere:
        stmt = stmt.where(TargetCandidate.is_centromere == False)
    if exon_only:
        stmt = stmt.where(TargetCandidate.is_exon == True)

    # 3. 统计总匹配数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    if gene_summary:
        gene_summary.filtered_candidates = total_count

    # 4. 排序处理
    sort_col = getattr(TargetCandidate, sort_by, TargetCandidate.efficiency_score)
    if sort_order.lower() == "asc":
        stmt = stmt.order_by(asc(sort_col).nulls_last())
    else:
        stmt = stmt.order_by(desc(sort_col).nulls_last())

    # 5. 分页执行
    offset_val = (page - 1) * page_size
    stmt = stmt.offset(offset_val).limit(page_size)

    items_res = await db.execute(stmt)
    items = list(items_res.scalars().all())

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return CandidatesResponse(
        items=items,
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        gene_summary=gene_summary,
    )
