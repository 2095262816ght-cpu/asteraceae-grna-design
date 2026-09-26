import io
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import AsyncSessionLocal
from backend.app.db.models import ScoringJob, ScoringJobItem
from cs_pipeline.core.sequence_spec import validate_seq30, calc_gc, calc_tm
from cs_pipeline.app.batch_importer import (
    read_uploaded_table,
    detect_sequence_column,
    detect_id_column,
    generate_template_csv,
    generate_template_excel,
)

try:
    from cs_pipeline.app.inference_client import InferenceClient
    _HAS_INFERENCE_CLIENT = True
except ImportError:
    _HAS_INFERENCE_CLIENT = False


async def create_batch_scoring_job(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
) -> dict:
    """解析上传的 CSV/Excel 文件，完成序列校验，创建并持久化批处理 Job 与 Items。"""
    filename_lower = filename.lower()
    if not (filename_lower.endswith(".csv") or filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls")):
        raise HTTPException(
            status_code=400,
            detail="仅支持上传 CSV (.csv) 或 Excel (.xlsx, .xls) 格式文件",
        )

    try:
        df = read_uploaded_table(file_bytes, filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(exc)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="上传的文件没有包含有效数据行")

    try:
        seq_col = detect_sequence_column(df)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"未能在表格中识别到合规的 30bp 序列列: {str(exc)}")

    id_col = detect_id_column(df, seq_col)

    job_id = str(uuid.uuid4())
    job_title = f"批量检测 - {filename}"
    total_count = len(df)

    job = ScoringJob(
        id=job_id,
        title=job_title,
        job_type="batch",
        status="pending",
        total_sequences=total_count,
        processed_sequences=0,
        duration_seconds=0.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)

    valid_count = 0
    invalid_count = 0
    items: List[ScoringJobItem] = []

    for idx, row in df.iterrows():
        raw_val = row[seq_col]
        seq_str = str(raw_val).strip() if pd.notna(raw_val) else ""

        custom_id = None
        if id_col and id_col in row and pd.notna(row[id_col]):
            custom_id = str(row[id_col]).strip()
        else:
            custom_id = f"gRNA_{idx + 1:03d}"

        err = validate_seq30(seq_str)
        if err is None:
            s = seq_str.upper()
            flank_5p = s[0:4]
            guide_seq = s[4:24]
            pam = s[24:27]
            flank_3p = s[27:30]
            gc_pct = round(calc_gc(guide_seq) * 100, 1)
            tm_c = round(calc_tm(guide_seq), 1)

            item = ScoringJobItem(
                job_id=job_id,
                custom_id=custom_id,
                seq30=s,
                flank_5p=flank_5p,
                guide_seq=guide_seq,
                pam=pam,
                flank_3p=flank_3p,
                gc_pct=gc_pct,
                tm_c=tm_c,
                is_valid=True,
                error_message=None,
            )
            valid_count += 1
        else:
            item = ScoringJobItem(
                job_id=job_id,
                custom_id=custom_id,
                seq30=seq_str,
                flank_5p=None,
                guide_seq=None,
                pam=None,
                flank_3p=None,
                gc_pct=None,
                tm_c=None,
                is_valid=False,
                error_message=err,
            )
            invalid_count += 1

        items.append(item)
        db.add(item)

    await db.commit()

    return {
        "job_id": job_id,
        "title": job_title,
        "status": "pending",
        "total_sequences": total_count,
        "processed_sequences": 0,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "created_at": job.created_at.isoformat(),
    }


async def run_batch_scoring_task(
    job_id: str,
    client: Optional[object] = None,
) -> None:
    """后台异步执行器：在独立数据库事务中驱动批处理模型推理与实时进度流转。"""
    async with AsyncSessionLocal() as session:
        job = await session.get(ScoringJob, job_id)
        if not job or job.status in ("completed", "failed"):
            return

        job.status = "running"
        await session.commit()

        t0 = time.time()

        try:
            # 查询全部待打分的合法 item
            stmt = (
                select(ScoringJobItem)
                .where(ScoringJobItem.job_id == job_id, ScoringJobItem.is_valid == True)  # noqa: E712
                .order_by(ScoringJobItem.id)
            )
            res = await session.execute(stmt)
            valid_items = list(res.scalars().all())

            # 若没有合法条目，直接标为完成
            if not valid_items:
                job.status = "completed"
                job.processed_sequences = job.total_sequences
                job.completed_at = datetime.now(timezone.utc)
                job.duration_seconds = round(time.time() - t0, 3)
                await session.commit()
                return

            seqs = [item.seq30 for item in valid_items]

            # 实例化或调用 InferenceClient
            if client is None and _HAS_INFERENCE_CLIENT:
                try:
                    client = InferenceClient()
                except Exception:
                    client = None

            inference_results = None
            if client is not None:
                try:
                    inference_results = client.score_sequences(seqs, timeout=180.0)
                except Exception as exc:
                    job.warning_message = f"批处理模型推理外部调用异常，触发降级计算: {str(exc)}"

            # 赋值并持久化每个 item 的打分
            for idx, item in enumerate(valid_items):
                deepspcas9_score = None
                crispron_source = "approximated"
                efficiency_score = None

                if inference_results is not None and not inference_results.raw_df.empty and idx < len(inference_results.raw_df):
                    row = inference_results.raw_df.iloc[idx]
                    if "deepspcas9_score" in row and row["deepspcas9_score"] is not None:
                        deepspcas9_score = round(float(row["deepspcas9_score"]), 2)
                    crispron_source = str(row.get("crispron_source", "approximated"))

                    for score_key in ("stacking_score", "efficiency_score", "efficiency_score_v21_nob879"):
                        if score_key in row and row[score_key] is not None:
                            efficiency_score = round(float(row[score_key]), 2)
                            break

                # 兜底启发式评分
                if efficiency_score is None:
                    gc = item.gc_pct if item.gc_pct is not None else 50.0
                    efficiency_score = round(max(10.0, min(95.0, 50.0 + (gc - 50.0) * 0.5)), 2)
                    crispron_source = "approximated"

                item.deepspcas9_score = deepspcas9_score
                item.crispron_source = crispron_source
                item.efficiency_score = efficiency_score

            # 所有条目（含无效条目）均算入 processed
            job.processed_sequences = job.total_sequences
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.duration_seconds = round(time.time() - t0, 3)

            await session.commit()

        except Exception as exc:
            job.status = "failed"
            job.error_message = f"批处理执行异常: {str(exc)}"
            job.completed_at = datetime.now(timezone.utc)
            job.duration_seconds = round(time.time() - t0, 3)
            await session.commit()
