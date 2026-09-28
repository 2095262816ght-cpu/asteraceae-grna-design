import asyncio
import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ExportBatch, GeneExpression, TargetCandidate
from backend.app.services.expression_evidence import derive_expression_evidence
from backend.app.services import offtarget_service

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符。"""
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', name.strip())
    return cleaned or "export_batch"


async def create_export_batch(
    name: str,
    format: str,
    candidate_ids: List[int],
    gene_id: Optional[str] = None,
    db: AsyncSession = None,
) -> ExportBatch:
    """创建并保存实验设计导出批次。"""
    if not candidate_ids:
        raise HTTPException(status_code=400, detail="导出批次必须至少包含一个候选靶点")

    fmt = format.lower()
    if fmt not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 csv 或 xlsx 格式导出")

    # 查重或校验候选靶点在数据库中是否存在
    stmt = select(TargetCandidate.id).where(TargetCandidate.id.in_(candidate_ids))
    res = await db.execute(stmt)
    found_ids = list(res.scalars().all())

    if not found_ids:
        raise HTTPException(status_code=404, detail="指定的候选靶点在数据库中均不存在")

    batch_id = str(uuid.uuid4())
    batch_name = name.strip() if name and name.strip() else f"gRNA优选批次_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    batch = ExportBatch(
        id=batch_id,
        name=batch_name,
        format=fmt,
        gene_id=gene_id,
        candidate_count=len(found_ids),
        candidate_ids=json.dumps(found_ids),
        created_at=datetime.now(timezone.utc),
    )

    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


async def generate_batch_export_bytes(
    batch_id: str,
    db: AsyncSession,
) -> Tuple[bytes, str, str]:
    """生成符合湿实验下单规范的标准 CSV 或 Excel 表格字节流。"""
    batch = await db.get(ExportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"未找到 ID 为 '{batch_id}' 的导出批次")

    try:
        cand_ids = json.loads(batch.candidate_ids)
    except Exception:
        cand_ids = [int(x.strip()) for x in batch.candidate_ids.split(",") if x.strip().isdigit()]

    stmt = (
        select(TargetCandidate)
        .where(TargetCandidate.id.in_(cand_ids))
        .order_by(TargetCandidate.efficiency_score.desc())
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates:
        raise HTTPException(status_code=404, detail="该批次对应的候选靶点数据不存在")

    # 路线B：脱靶计数按需补算（按 seq20 去重计数，回填缓存；基因组不可用时如实标"未计算"）
    missing = [c for c in candidates if c.offtarget_count_mis3 is None]
    if missing:
        try:
            counts = await asyncio.to_thread(
                offtarget_service.compute_offtarget_counts, [c.seq20 for c in missing]
            )
            for c in missing:
                c.offtarget_count_mis3 = counts.get(c.seq20.upper())
            await db.commit()
        except Exception:
            logger.warning("脱靶计数按需计算失败，导出将标注'未计算'", exc_info=True)

    # 基因级表达证据（crosswalk × 表达矩阵），候选级缺失时派生状态与说明
    gene_ids = {c.gene_id for c in candidates}
    res = await db.execute(select(GeneExpression).where(GeneExpression.gene_id.in_(gene_ids)))
    expr_map = {e.gene_id: e for e in res.scalars().all()}

    records = []
    for rank, c in enumerate(candidates, start=1):
        _, expr_display, expr_note = derive_expression_evidence(c.expression_status, expr_map.get(c.gene_id))
        records.append({
            "实验优选推荐序": rank,
            "靶点唯一ID": c.id,
            "目标基因": c.gene_id,
            "染色体": c.chrom,
            "基因组起始": c.start,
            "基因组终止": c.end,
            "链向": c.strand,
            "30bp完整靶位点": c.seq30,
            "20bp_Guide序列": c.seq20,
            "3bp_PAM(gRNA链方向，恒为NGG；负链靶点在基因组正链读作CCN)": c.pam,
            "GC含量(%)": c.gc_pct,
            "解链温度_Tm(C)": c.tm_c,
            "综合排序效率分": c.efficiency_score,
            "组织优先指数(叶)": c.priority_score_leaf,
            "组织优先指数(根)": c.priority_score_root,
            "功能性脱靶危害(叶)": c.hazard_leaf,
            "功能性脱靶危害(根)": c.hazard_root,
            "表达证据状态": expr_display,
            "表达证据说明": expr_note,
            "面板内位点数": c.n_intra_panel_sites if c.n_intra_panel_sites is not None else "不适用（面板仅覆盖49个NLR基因）",
            "DeepSpCas9活性分": c.deepspcas9_score,
            "CRISPRon活性分": c.crispron_score,
            "潜在脱靶位点数(<=3)": c.offtarget_count_mis3 if c.offtarget_count_mis3 is not None else "未计算",
            "是否外显子": "是" if c.is_exon else "否",
            "是否着丝粒区": "是" if c.is_centromere else "否",
        })

    df = pd.DataFrame(records)
    clean_name = sanitize_filename(batch.name)

    if batch.format == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="gRNA实验设计优选清单", index=False)
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{clean_name}_{batch.id[:8]}.xlsx"
    else:
        content = df.to_csv(index=False).encode("utf-8-sig")
        media_type = "text/csv"
        filename = f"{clean_name}_{batch.id[:8]}.csv"

    return content, media_type, filename
