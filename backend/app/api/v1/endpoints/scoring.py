from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.scoring_service import execute_single_scoring

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


@router.post("/scoring/single", response_model=SingleScoringResponse, summary="单序列 30bp 实时打分与持久化")
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
