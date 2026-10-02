from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.db.models import Base
from backend.app.db.seed import seed_candidates_if_empty
from backend.app.db.session import engine, sync_missing_columns


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保数据库表存在并自动完成 Seed 数据灌入（旧库缺列自动补齐）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(sync_missing_columns)
    await seed_candidates_if_empty()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 配置 CORS 跨域通信
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"欢迎使用 {settings.PROJECT_NAME} API 服务",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
