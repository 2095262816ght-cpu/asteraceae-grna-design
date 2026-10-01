import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ScoringJob, ScoringJobItem
from cs_pipeline.core.sequence_spec import validate_seq30, calc_gc, calc_tm

# 特征构建单一来源：与训练/推理同口径（features_common.seq_features）
try:
    import pandas as pd
    from cs_pipeline.scripts.features_common import seq_features
    _HAS_FEATURES = True
except Exception:
    pd = None
    seq_features = None
    _HAS_FEATURES = False

# 尝试导入 InferenceClient；在特殊无独立 Conda 环境的测试中支持优雅平滑降级
try:
    from cs_pipeline.app.inference_client import InferenceClient
    _HAS_INFERENCE_CLIENT = True
except ImportError:
    _HAS_INFERENCE_CLIENT = False


async def execute_single_scoring(
    seq30: str,
    title: Optional[str] = None,
    db: AsyncSession = None,
    client: Optional[object] = None,
) -> dict:
    """执行单序列 30bp 规范性校验、深度模型打分与持久化入库。"""
    # 1. 序列规格强校验
    err = validate_seq30(seq30)
    if err:
        raise HTTPException(status_code=400, detail=f"序列规格错误: {err}")

    s = seq30.strip().upper()
    flank_5p = s[0:4]
    guide_seq = s[4:24]
    pam = s[24:27]
    flank_3p = s[27:30]
    gc_pct = round(calc_gc(guide_seq) * 100, 1)
    tm_c = round(calc_tm(guide_seq), 1)

    t0 = time.time()
    deepspcas9_score = None
    crispron_score = None
    crispron_source = "approximated"
    efficiency_score = None
    warning_msg = None

    # 2. 调度推理客户端
    if client is None and _HAS_INFERENCE_CLIENT:
        try:
            client = InferenceClient()
        except Exception:
            client = None

    if client is not None:
        try:
            # 推理为同步阻塞调用：放入线程池，避免卡死事件循环导致其他请求无响应
            inference_res = await asyncio.to_thread(client.score_sequences, [s], timeout_s=60)
            if not inference_res.raw_df.empty:
                row = inference_res.raw_df.iloc[0]
                deepspcas9_score = (
                    round(float(row["deepspcas9_score"]), 2)
                    if "deepspcas9_score" in row and row["deepspcas9_score"] is not None
                    else None
                )
                crispron_score = (
                    round(float(row["crispron_score"]), 2)
                    if "crispron_score" in row and row["crispron_score"] is not None
                    else None
                )
                crispron_source = str(row.get("crispron_source", "approximated"))
                # 优先获取 stacking_score 或 efficiency_score
                for score_key in ("stacking_score", "efficiency_score", "efficiency_score_v21_nob879"):
                    if score_key in row and row[score_key] is not None:
                        efficiency_score = round(float(row[score_key]), 2)
                        break

            if inference_res.has_approximated:
                warning_msg = inference_res.warning_message
        except Exception as exc:
            warning_msg = f"模型推理子进程触发兜底降级: {str(exc)}"

    # 若未能从外部模型获取分数，根据序列 GC/Tm 经验公式生成基准分
    if efficiency_score is None:
        efficiency_score = round(max(10.0, min(95.0, 50.0 + (gc_pct - 50.0) * 0.5)), 2)
        crispron_source = "approximated"

    latency = round(time.time() - t0, 3)
    job_id = str(uuid.uuid4())
    job_title = title.strip() if title and title.strip() else f"单序列打分 ({guide_seq[:8]}...)"

    # 特征向量（单一来源 seq_features：gc_total/gc_seed/tm/poly_t/pam_n_ACGT）
    features = None
    if _HAS_FEATURES:
        try:
            frow = seq_features(pd.Series([s], dtype=str)).iloc[0]
            features = {k: float(v) for k, v in frow.items()}
        except Exception:
            features = None

    # 3. 构造持久化实体
    job = ScoringJob(
        id=job_id,
        title=job_title,
        job_type="single",
        status="completed",
        total_sequences=1,
        processed_sequences=1,
        duration_seconds=latency,
        crispron_source=crispron_source,
        warning_message=warning_msg,
        completed_at=datetime.now(timezone.utc),
    )

    item = ScoringJobItem(
        job_id=job_id,
        seq30=s,
        flank_5p=flank_5p,
        guide_seq=guide_seq,
        pam=pam,
        flank_3p=flank_3p,
        gc_pct=gc_pct,
        tm_c=tm_c,
        deepspcas9_score=deepspcas9_score,
        crispron_source=crispron_source,
        efficiency_score=efficiency_score,
    )

    if db is not None:
        db.add(job)
        db.add(item)
        await db.commit()

    return {
        "job_id": job_id,
        "title": job_title,
        "seq30": s,
        "flank_5p": flank_5p,
        "guide_seq": guide_seq,
        "pam": pam,
        "flank_3p": flank_3p,
        "gc_pct": gc_pct,
        "tm_c": tm_c,
        "deepspcas9_score": deepspcas9_score,
        "crispron_score": crispron_score,
        "crispron_source": crispron_source,
        "efficiency_score": efficiency_score,
        "features": features,
        "warning_message": warning_msg,
        "duration_seconds": latency,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
