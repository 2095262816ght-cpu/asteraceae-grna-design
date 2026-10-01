from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, candidates, scoring, exports, annotation, offtarget, meta

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(candidates.router, tags=["Candidates & Genes"])
api_router.include_router(scoring.router, tags=["Scoring Pipeline"])
api_router.include_router(exports.router, tags=["Exports & Batches"])
api_router.include_router(annotation.router, tags=["Sequence Annotation"])
api_router.include_router(offtarget.router, tags=["Off-target Details"])
api_router.include_router(meta.router, tags=["Methods & Versions"])

