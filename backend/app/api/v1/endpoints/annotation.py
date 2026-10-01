"""Tab 2 自定义序列三态注释端点（C4/C5/C6 + D1 参考包路由）。

POST /api/v1/sequence/annotate —— seq30 基因组回贴与按需多组学：
- precomputed：命中预计算候选表，复用多组学列（与 Tab 1 同源同值）；
- annotated：精确匹配参考包基因组（预置 lettuce/tks 或用户导入包），注释基因座 + 按需脱靶 + 按需方案3 优先指数；
- custom：未命中基因组，未锚定，多组学如实标注不适用。

GET /api/v1/sequence/bundles —— 参考包清单（预置 + 用户导入，含证据可用性）。
POST /api/v1/sequence/bundles —— 服务端路径注册参考包（D2 导入）。
"""
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services import reference_bundle_service as rb_service
from backend.app.services.sequence_annotation_service import annotate_seq30
from cs_pipeline.core.sequence_spec import validate_seq30

router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 直传仅收 ≤50MB 小文件；大基因组走服务端路径注册


class AnnotateRequest(BaseModel):
    seq30: str = Field(..., description="30bp 靶位点序列（4+20+3+3 布局）")
    species: str = Field(
        "lettuce", description="参考包 ID：预置 lettuce（莴苣 T2T）/ tks（橡胶草），或用户导入包 ID"
    )
    bundle_id: Optional[str] = Field(None, description="参考包 ID（species 的显式写法，优先）")
    efficiency_score: Optional[float] = Field(
        None, description="该序列的预测效率分（用于按需方案3 百分位；缺省则不算优先指数）"
    )
    compute_offtarget: bool = Field(True, description="是否执行按需脱靶计数（全基因组扫描，秒级）")
    peer_efficiency_scores: Optional[List[float]] = Field(
        None, description="同批其他序列的效率分（贴入集合百分位口径；缺省则无集合不排名）"
    )


class BundleRegisterRequest(BaseModel):
    bundle_id: str = Field(..., description="参考包 ID（小写字母/数字/下划线/连字符）")
    display_name: str = Field(..., description="展示名")
    fasta_path: str = Field(..., description="参考基因组 FASTA 服务端路径（绝对或仓库相对）")
    gff_path: Optional[str] = Field(None, description="GFF3 基因注释路径（可选）")
    expression_path: Optional[str] = Field(None, description="表达矩阵 csv/xlsx 路径（可选）")
    tissue_columns: Optional[Dict[str, str]] = Field(
        None, description='组织列映射 {"叶": "Leaf_tpm", ...}（表达矩阵列名）'
    )
    expression_id_rule: str = Field("same", description="基因 ID 匹配规则: same | evm_tu_to_model")
    notes: Optional[str] = Field(None, description="备注（口径/来源说明）")
    allow_overwrite: bool = Field(False, description="同 ID 已存在时是否覆盖")


@router.post("/sequence/annotate", summary="自定义 seq30 基因组回贴三态注释与按需多组学")
async def annotate_sequence(
    req: AnnotateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    err = validate_seq30(req.seq30)
    if err:
        return {"state": "invalid", "error": f"序列规格错误: {err}"}
    bundle_id = req.bundle_id or req.species or "lettuce"
    try:
        return await annotate_seq30(
            req.seq30,
            db,
            bundle_id=bundle_id,
            efficiency_score=req.efficiency_score,
            compute_offtarget=req.compute_offtarget,
            peer_efficiency_scores=req.peer_efficiency_scores,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/sequence/bundles", summary="参考包清单（预置 + 用户导入）")
async def list_bundles(db: AsyncSession = Depends(get_db)) -> list:
    return await rb_service.list_bundles(db)


@router.get("/annotation/gene-structure", summary="基因结构注释（外显子/内含子/CDS/TSS/蛋白功能域）")
async def get_gene_structure(
    gene_id: str = Query(..., description="基因 ID，例如 LsT2T1G000010"),
    bundle_id: str = Query("lettuce", description="参考包 ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from backend.app.services import gene_structure_service as gs_service

    try:
        bundle = await rb_service.resolve_bundle(db, bundle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if bundle.gff is None or not bundle.gff.exists():
        return {
            "gene_id": gene_id,
            "available": False,
            "missing_requirements": [f"参考包 {bundle.id} 无基因注释 GFF，基因结构不可用（如实标注，不编造）"],
        }
    import asyncio

    rec = await asyncio.to_thread(gs_service.gene_structure, bundle.gff, gene_id)
    if rec is None:
        return {
            "gene_id": gene_id,
            "available": False,
            "missing_requirements": [f"GFF 中未找到基因 {gene_id}（ID 命名空间可能不同）"],
        }
    return {
        "gene_id": gene_id,
        "available": True,
        "bundle_id": bundle.id,
        **rec,
        "domain_note": (
            "蛋白功能域来自离线注释（NLR-Annotator/HMMER，GFF 不含结构域信息）"
            if rec.get("domains")
            else "暂无蛋白功能域注释（domain_annotations.csv 缺省或未覆盖该基因）"
        ),
    }


@router.post("/sequence/bundles", summary="服务端路径注册参考包（导入）")
async def register_bundle(
    req: BundleRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await rb_service.register_bundle(
            db,
            bundle_id=req.bundle_id,
            display_name=req.display_name,
            fasta_path=req.fasta_path,
            gff_path=req.gff_path,
            expression_path=req.expression_path,
            tissue_columns=req.tissue_columns,
            expression_id_rule=req.expression_id_rule,
            notes=req.notes,
            allow_overwrite=req.allow_overwrite,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sequence/bundles/upload", summary="小文件直传（≤50MB）落服务端参考包目录，返回服务端路径")
async def upload_reference_file(file: UploadFile = File(...)) -> dict:
    dest_dir = rb_service.REFERENCE_DIR / "imports"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(file.filename or "upload.bin").name  # .name 剥掉任何路径成分，防穿越
    size = 0
    try:
        with open(dest, "wb") as fh:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件超过直传上限 50MB：大基因组请放到服务端 {rb_service.REFERENCE_DIR} 后用路径注册",
                    )
                fh.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    return {"path": str(dest), "size_bytes": size, "filename": dest.name}
