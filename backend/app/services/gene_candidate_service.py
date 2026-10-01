"""D3 档②：现场枚举同基因候选分布 + 批量打分（Tab 1 百分位真同口径）。

库内预计算候选分布只覆盖已灌库基因；导入参考包锚定的基因没有现成分布。
本模块在参考包基因组上枚举该基因（编码区 + TSS 上游 2kb 启动子近似）全部 NGG 候选，
批量调用同一推理管线打 efficiency 分，构造与 Tab 1 完全同口径的基因内分布
（rank(pct=True)）。按 (参考包, 基因, 基因组 mtime) 进程内缓存，同基因只算一次。

口径纪律：枚举/打分不可用时返回 None 由调用方如实标注缺失，绝不硬猜数值。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.services import offtarget_service
from backend.app.services.gene_structure_service import PROMOTER_UPSTREAM
from backend.app.services.reference_bundle_service import ResolvedBundle

logger = logging.getLogger(__name__)

MAX_ENUM_CANDIDATES = 2000
_CACHE_MAX = 64
_dist_cache: Dict[tuple, dict] = {}

try:
    from cs_pipeline.app.inference_client import InferenceClient

    _HAS_INFERENCE_CLIENT = True
except ImportError:
    _HAS_INFERENCE_CLIENT = False

_score_cache: Dict[str, float] = {}


def _revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


def _find_record(fasta: Path, chrom: str):
    recs = offtarget_service._load_fai(fasta)
    by_name = {r[0]: r for r in recs}
    for cand in (chrom, chrom.replace("chr", "Chr").replace("CHR", "Chr"), chrom.replace("Chr", "chr")):
        if cand in by_name:
            return by_name[cand]
    return None


def enumerate_gene_seq30(
    fasta: Path,
    chrom: str,
    gene_start: int,
    gene_end: int,
    strand: str,
    promoter: int = PROMOTER_UPSTREAM,
    cap: int = MAX_ENUM_CANDIDATES,
) -> Tuple[List[str], str]:
    """枚举基因窗口（编码区 + 链感知启动子近似）内双链全部 NGG 候选 seq30。

    返回 (seq30 列表, 枚举口径说明)。窗口不完整 30-mer 跳过；同 seq30 去重保序。
    """
    if strand == "+":
        lo, hi = gene_start - promoter, gene_end
    elif strand == "-":
        lo, hi = gene_start, gene_end + promoter
    else:
        lo, hi = gene_start - promoter, gene_end + promoter
    lo = max(lo, 1)

    rec = _find_record(fasta, chrom)
    if rec is None:
        return [], f"参考包基因组中无染色体 {chrom}"
    raw = offtarget_service._fetch(fasta, rec, lo - 1, hi)
    w = raw.decode("ascii", "ignore").upper()
    if len(w) < 30:
        return [], "基因窗口过短，无法构成 30-mer 候选"

    out: List[str] = []
    seen = set()
    n_poly_t = 0

    def _scan(seq: str) -> None:
        nonlocal n_poly_t
        for i in range(len(seq) - 29):
            if len(out) >= cap:
                return
            pam = seq[i + 24 : i + 27]
            if pam[0] in "ACGT" and pam[1] == "G" and pam[2] == "G":
                s30 = seq[i : i + 30]
                if s30 not in seen:
                    seen.add(s30)
                    # poly-T 硬过滤（教师口径）：U6 转录遇 TTTT 提前终止，必须避免
                    if "TTTT" in s30[4:24]:
                        n_poly_t += 1
                        continue
                    out.append(s30)

    _scan(w)
    _scan(_revcomp(w))
    note = (
        f"现场枚举该基因 {'编码区' if strand in '+-' else '基因体'}+TSS 上游 {promoter}bp 窗口 "
        f"({chrom}:{lo}-{hi}) 双链全部 NGG 候选 {len(out)} 条"
        + (f"（另 {n_poly_t} 条含 TTTT poly-T 终止信号已硬过滤）" if n_poly_t else "")
        + ("（已达枚举上限，截断）" if len(out) >= cap else "")
    )
    return out, note


def _extract_efficiency(row) -> Optional[float]:
    for key in ("stacking_score", "efficiency_score", "efficiency_score_v21_nob879"):
        if key in row and row[key] is not None:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return None


def score_seq30_batch(seq30s: List[str], client: Optional[object] = None) -> Optional[Dict[str, float]]:
    """批量打 efficiency 分（与 Tab 1 预计算同源 v2.1 口径）；不可用返回 None，不硬猜。"""
    todo = [s for s in dict.fromkeys(seq30s) if s not in _score_cache]
    if todo:
        if client is None and _HAS_INFERENCE_CLIENT:
            try:
                client = InferenceClient()
            except Exception:
                client = None
        if client is None:
            return None
        try:
            res = client.score_sequences(todo, timeout_s=600)
        except Exception as exc:
            logger.warning("候选分布批量打分失败: %s", exc)
            return None
        raw = getattr(res, "raw_df", None)
        if raw is None or raw.empty:
            return None
        for idx, s in enumerate(todo):
            if idx < len(raw):
                eff = _extract_efficiency(raw.iloc[idx])
                if eff is not None:
                    _score_cache[s] = eff
    return {s: _score_cache[s] for s in dict.fromkeys(seq30s) if s in _score_cache}


def gene_efficiency_distribution(
    bundle: ResolvedBundle,
    chrom: str,
    gene: dict,
    own_seq30: str,
    own_efficiency: float,
    client: Optional[object] = None,
) -> Optional[Tuple[List[float], str]]:
    """基因内 efficiency 分布（不含自身；自身分由调用方并入排名）。

    返回 (分布分数列表, 口径说明)；枚举或打分不可用返回 None（不硬猜）。
    """
    if bundle.fasta is None:
        return None
    try:
        mtime = bundle.fasta.stat().st_mtime
    except OSError:
        return None
    key = (bundle.id, gene.get("gene_id"), gene.get("start"), gene.get("end"), gene.get("strand"), mtime)
    cached = _dist_cache.get(key)
    if cached is None:
        seq30s, enum_note = enumerate_gene_seq30(
            bundle.fasta, chrom, int(gene["start"]), int(gene["end"]), str(gene.get("strand", ""))
        )
        if not seq30s:
            logger.warning("候选枚举为空: %s", enum_note)
            return None
        scores = score_seq30_batch(seq30s, client=client)
        if scores is None:
            return None
        cached = {"scores": scores, "note": enum_note, "n_seq": len(seq30s)}
        if len(_dist_cache) >= _CACHE_MAX:
            _dist_cache.pop(next(iter(_dist_cache)))
        _dist_cache[key] = cached

    own = own_seq30.strip().upper()
    dist = [sc for s, sc in cached["scores"].items() if s != own]
    if not dist:
        return None
    note = f"{cached['note']}，批量打分得有效分布 {len(dist) + 1} 条（含自身）"
    return dist, note
