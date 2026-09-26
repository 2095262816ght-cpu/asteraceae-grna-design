from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.db.session import check_database_health

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: str


@router.get("/health", response_model=HealthResponse, summary="系统健康检查")
async def health_check() -> HealthResponse:
    db_ok = await check_database_health()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=settings.VERSION,
        database="connected" if db_ok else "disconnected",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
