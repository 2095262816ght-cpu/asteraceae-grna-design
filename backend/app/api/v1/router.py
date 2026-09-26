from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, candidates

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(candidates.router, tags=["Candidates & Genes"])
