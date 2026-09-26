from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.db.models import ExportBatch
from backend.app.services.export_service import (
    create_export_batch,
    generate_batch_export_bytes,
)

router = APIRouter()


class CreateExportBatchRequest(BaseModel):
    name: str = Field(
        ...,
        description="导出批次自定义名称",
        json_schema_extra={"example": "LsaT2T01G023690 优选候选批次"},
    )
    format: str = Field(
        "csv",
        pattern="^(csv|xlsx)$",
        description="导出文件格式：csv 或 xlsx",
    )
    candidate_ids: List[int] = Field(
        ...,
        min_length=1,
        description="选中的靶点候选 ID 数组",
        json_schema_extra={"example": [1, 2, 3]},
    )
    gene_id: Optional[str] = Field(
        None,
        description="所属基因座 ID",
        json_schema_extra={"example": "LsaT2T01G023690"},
    )


class ExportBatchResponse(BaseModel):
    id: str
    name: str
    format: str
    gene_id: Optional[str] = None
    candidate_count: int
    created_at: str


@router.post(
    "/exports",
    response_model=ExportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建并持久化实验设计导出批次",
)
async def create_batch(
    payload: CreateExportBatchRequest,
    db: AsyncSession = Depends(get_db),
) -> ExportBatchResponse:
    batch = await create_export_batch(
        name=payload.name,
        format=payload.format,
        candidate_ids=payload.candidate_ids,
        gene_id=payload.gene_id,
        db=db,
    )
    return ExportBatchResponse(
        id=batch.id,
        name=batch.name,
        format=batch.format,
        gene_id=batch.gene_id,
        candidate_count=batch.candidate_count,
        created_at=batch.created_at.isoformat(),
    )


@router.get(
    "/exports",
    response_model=List[ExportBatchResponse],
    summary="获取历史实验设计导出批次列表",
)
async def list_export_batches(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[ExportBatchResponse]:
    stmt = (
        select(ExportBatch)
        .order_by(ExportBatch.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    batches = result.scalars().all()
    return [
        ExportBatchResponse(
            id=b.id,
            name=b.name,
            format=b.format,
            gene_id=b.gene_id,
            candidate_count=b.candidate_count,
            created_at=b.created_at.isoformat(),
        )
        for b in batches
    ]


@router.get(
    "/exports/{batch_id}/download",
    summary="下载批次文件 (CSV / Excel)",
)
async def download_export_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
):
    content, media_type, filename = await generate_batch_export_bytes(
        batch_id=batch_id,
        db=db,
    )
    from urllib.parse import quote
    encoded_filename = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"
        },
    )
