from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.session import get_db
from backend.app.db.models import ScoringJob, ScoringJobItem
from backend.app.services.scoring_service import execute_single_scoring
from backend.app.services.batch_service import (
    create_batch_scoring_job,
    run_batch_scoring_task,
)
from cs_pipeline.app.batch_importer import (
    generate_template_csv,
    generate_template_excel,
)

router = APIRouter()


class SingleScoringRequest(BaseModel):
    seq30: str = Field(
        ...,
        description="30bp 完整靶位点序列 (4nt flank + 20nt guide + 3nt PAM + 3nt flank)",
        json_schema_extra={"example": "TTTGTGGATTCCGGTAGAATCTGATGGAAT"},
    )
    title: Optional[str] = Field(
        None,
        description="任务自定义备注名称",
        json_schema_extra={"example": "测试靶点"},
    )


class SingleScoringResponse(BaseModel):
    job_id: str
    title: str
    seq30: str
    flank_5p: str
    guide_seq: str
    pam: str
    flank_3p: str
    gc_pct: float
    tm_c: float
    deepspcas9_score: Optional[float] = None
    crispron_source: Optional[str] = None
    efficiency_score: Optional[float] = None
    warning_message: Optional[str] = None
    duration_seconds: float
    created_at: str


class BatchUploadResponse(BaseModel):
    job_id: str
    title: str
    status: str
    total_sequences: int
    processed_sequences: int
    valid_count: int
    invalid_count: int
    created_at: str


class ScoringJobItemDetail(BaseModel):
    id: int
    custom_id: Optional[str] = None
    seq30: str
    flank_5p: Optional[str] = None
    guide_seq: Optional[str] = None
    pam: Optional[str] = None
    flank_3p: Optional[str] = None
    gc_pct: Optional[float] = None
    tm_c: Optional[float] = None
    deepspcas9_score: Optional[float] = None
    crispron_source: Optional[str] = None
    efficiency_score: Optional[float] = None
    is_valid: bool
    error_message: Optional[str] = None


class ScoringJobDetailResponse(BaseModel):
    job_id: str
    title: str
    job_type: str
    status: str
    total_sequences: int
    processed_sequences: int
    progress_pct: float
    duration_seconds: float
    warning_message: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    items: List[ScoringJobItemDetail] = []


@router.post(
    "/scoring/single",
    response_model=SingleScoringResponse,
    summary="单序列 30bp 实时打分与持久化",
)
async def score_single(
    payload: SingleScoringRequest,
    db: AsyncSession = Depends(get_db),
) -> SingleScoringResponse:
    res = await execute_single_scoring(
        seq30=payload.seq30,
        title=payload.title,
        db=db,
    )
    return SingleScoringResponse(**res)


@router.get(
    "/scoring/template",
    summary="下载批量序列检测标准模板 (CSV / Excel)",
)
async def download_template(
    format: str = Query("csv", pattern="^(csv|xlsx)$", description="模板格式：csv 或 xlsx"),
):
    if format == "csv":
        content = generate_template_csv()
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="grna_batch_template.csv"'},
        )
    else:
        content = generate_template_excel()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="grna_batch_template.xlsx"'},
        )


@router.post(
    "/scoring/upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="上传 CSV/Excel 批量启动异步打分流水线",
)
async def upload_batch_scoring(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="待解析的表格文件 (.csv, .xlsx, .xls)"),
    db: AsyncSession = Depends(get_db),
) -> BatchUploadResponse:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传的文件内容为空")

    job_info = await create_batch_scoring_job(
        file_bytes=file_bytes,
        filename=file.filename or "upload.csv",
        db=db,
    )

    # 调度后台异步模型推理任务
    background_tasks.add_task(run_batch_scoring_task, job_info["job_id"])

    return BatchUploadResponse(**job_info)


@router.get(
    "/scoring/jobs/{job_id}",
    response_model=ScoringJobDetailResponse,
    summary="轮询获取打分任务状态机进度与详情",
)
async def get_scoring_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> ScoringJobDetailResponse:
    stmt = (
        select(ScoringJob)
        .options(selectinload(ScoringJob.items))
        .where(ScoringJob.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"未找到 ID 为 '{job_id}' 的打分任务")

    total = job.total_sequences or 0
    processed = job.processed_sequences or 0
    progress_pct = round((processed / total * 100.0), 1) if total > 0 else 0.0

    items_detail = [
        ScoringJobItemDetail(
            id=item.id,
            custom_id=item.custom_id,
            seq30=item.seq30,
            flank_5p=item.flank_5p,
            guide_seq=item.guide_seq,
            pam=item.pam,
            flank_3p=item.flank_3p,
            gc_pct=item.gc_pct,
            tm_c=item.tm_c,
            deepspcas9_score=item.deepspcas9_score,
            crispron_source=item.crispron_source,
            efficiency_score=item.efficiency_score,
            is_valid=item.is_valid,
            error_message=item.error_message,
        )
        for item in sorted(job.items, key=lambda x: x.id)
    ]

    return ScoringJobDetailResponse(
        job_id=job.id,
        title=job.title,
        job_type=job.job_type,
        status=job.status,
        total_sequences=total,
        processed_sequences=processed,
        progress_pct=progress_pct,
        duration_seconds=job.duration_seconds or 0.0,
        warning_message=job.warning_message,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        items=items_detail,
    )
