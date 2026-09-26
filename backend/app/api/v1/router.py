from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, candidates, scoring, exports

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(candidates.router, tags=["Candidates & Genes"])
api_router.include_router(scoring.router, tags=["Scoring Pipeline"])
api_router.include_router(exports.router, tags=["Exports & Batches"])

