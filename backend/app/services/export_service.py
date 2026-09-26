import io
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ExportBatch, TargetCandidate


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

    records = []
    for rank, c in enumerate(candidates, start=1):
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
            "3bp_PAM": c.pam,
            "GC含量(%)": c.gc_pct,
            "解链温度_Tm(C)": c.tm_c,
            "综合排序效率分": c.efficiency_score,
            "DeepSpCas9活性分": c.deepspcas9_score,
            "CRISPRon活性分": c.crispron_score,
            "潜在脱靶位点数(<=3)": c.offtarget_count_mis3,
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
