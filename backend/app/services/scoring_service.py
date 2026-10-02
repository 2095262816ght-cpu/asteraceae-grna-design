import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import NamedTuple, Optional
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

# 效率分取值优先级：集成 stacking_score > efficiency_score > v2.1 noB879
_EFFICIENCY_SCORE_KEYS = ("stacking_score", "efficiency_score", "efficiency_score_v21_nob879")


class ModelScores(NamedTuple):
    """推理结果单行的模型分提取产物；缺失一律 None（不硬猜）。"""

    deepspcas9_score: Optional[float]
    crispron_score: Optional[float]
    crispron_source: Optional[str]
    efficiency_score: Optional[float]


_NO_MODEL_SCORES = ModelScores(None, None, None, None)


def _round2(value) -> Optional[float]:
    return round(float(value), 2) if value is not None else None


def extract_model_scores(row) -> ModelScores:
    """从推理结果单行提取模型分（单条与批处理共用同一口径）。

    crispron_source 是 CrispronScorer 不变量的纯透传：调用方不裁决不补标签，
    缺失即 None。row 为 None（如批处理本块未产出结果）时整体返回缺失。
    """
    if row is None:
        return _NO_MODEL_SCORES
    src = row.get("crispron_source")
    efficiency_score = None
    for key in _EFFICIENCY_SCORE_KEYS:
        value = row.get(key)
        if value is not None:
            efficiency_score = round(float(value), 2)
            break
    return ModelScores(
        deepspcas9_score=_round2(row.get("deepspcas9_score")),
        crispron_score=_round2(row.get("crispron_score")),
        crispron_source=str(src) if src else None,
        efficiency_score=efficiency_score,
    )


def append_warning(existing: Optional[str], note: str) -> str:
    """警示文案只追加不吞掉：缺失标注（「未计算」）永不被覆盖或跳过。"""
    return f"{existing}；{note}" if existing else note


async def execute_single_scoring(
    seq30: str,
    title: Optional[str] = None,
    bundle_id: Optional[str] = None,
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
    crispron_source = None
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
                deepspcas9_score, crispron_score, crispron_source, efficiency_score = extract_model_scores(
                    inference_res.raw_df.iloc[0]
                )

            if inference_res.has_approximated:
                warning_msg = inference_res.warning_message
        except Exception as exc:
            warning_msg = f"模型推理失败，模型分未计算: {exc}"

    # 口径纪律：模型分不可用时如实标缺失，不以 GC 启发式公式编造数值
    # （对齐 gene_candidate_service「不硬猜」与 CrispronScorer「绝不冒充」不变量）
    if efficiency_score is None:
        warning_msg = append_warning(
            warning_msg, "模型推理未产出 efficiency_score，该指标未计算（如实标注缺失，不编造数值）"
        )

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
        bundle_id=bundle_id,
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
