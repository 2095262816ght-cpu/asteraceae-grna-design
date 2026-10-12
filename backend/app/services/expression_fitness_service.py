"""gRNA 表达适配度（教师反馈 #2）：poly-T 硬过滤、5'G 偏好、spacer-only 二级结构 MFE。

- poly-T：U6 启动子（RNA Pol III）遇 TTTT 提前终止转录，含 TTTT 的 spacer 在候选
  枚举阶段硬过滤（"必须避免"）；
- 5'G：U6 转录起始偏好 G，5' 为 G 提高表达（加分标记，不作硬过滤）；
- MFE：仅 20nt spacer 自身折叠的最小自由能（ViennaRNA RNAfold，不含 scaffold 骨架序列）。
  风险阈值 ΔG < -5 kcal/mol（gRNA 文库筛选数据荟萃分析）——很可能抑制靶向活性；
  优先选 MFE 负值更小（更接近 0 或正值）的候选。MFE 只是参考维度，非绝对判据，
  需与 GC、脱靶、染色质开放状态综合判断。

口径纪律：ViennaRNA 不可用时 MFE 如实返回 None 并标注缺失，绝不编造数值。
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)

MFE_RISK_THRESHOLD = -5.0  # kcal/mol，spacer-only 口径
POLY_T_PATTERN = re.compile(r"TTTT")

_mfe_cache: Dict[str, Optional[float]] = {}
_RNA = None
_RNA_checked = False


def _rna_module():
    """延迟加载 ViennaRNA python 绑定；不可用返回 None。"""
    global _RNA, _RNA_checked
    if not _RNA_checked:
        _RNA_checked = True
        try:
            import RNA  # type: ignore

            _RNA = RNA
        except Exception as exc:
            logger.info("ViennaRNA python 绑定不可用（MFE 将缺失）: %s", exc)
            _RNA = None
    return _RNA


def has_poly_t(seq: str) -> bool:
    """含 TTTT（或更长 T 串）→ True（应硬过滤）。"""
    return bool(POLY_T_PATTERN.search(seq.upper()))


def starts_with_g(seq: str) -> bool:
    """5' 端为 G（U6 转录起始偏好）。"""
    return seq.upper().startswith("G")


def spacer_mfe(seq20: str) -> Optional[float]:
    """20nt spacer 自折叠最小自由能（kcal/mol，负值越小折叠越稳定）。

    仅计算 spacer 本身（教师口径：不拼接 scaffold 骨架序列）。
    ViennaRNA python 绑定优先，其次 PATH 上的 RNAfold CLI；均不可用返回 None。
    """
    seq20 = seq20.strip().upper()
    if len(seq20) != 20 or any(b not in "ACGT" for b in seq20):
        raise ValueError(f"spacer_mfe 需要 20nt ACGT: {seq20!r}")
    if seq20 in _mfe_cache:
        return _mfe_cache[seq20]

    rna_seq = seq20.replace("T", "U")
    mfe: Optional[float] = None
    RNA = _rna_module()
    try:
        if RNA is not None:
            fc = RNA.fold_compound(rna_seq)
            _, mfe = fc.mfe()
            mfe = float(mfe)
        elif shutil.which("RNAfold"):
            proc = subprocess.run(
                ["RNAfold", "--noPS"],
                input=f">s\n{rna_seq}\n",
                capture_output=True,
                text=True,
                timeout=30,
            )
            m = re.search(r"\(\s*(-?\d+\.\d+)\)", proc.stdout)
            if m:
                mfe = float(m.group(1))
        else:
            logger.info("ViennaRNA 不可用（无 RNA 绑定且 PATH 无 RNAfold），MFE 缺失")
    except Exception as exc:
        logger.warning("MFE 计算失败 %s: %s", seq20, exc)
        mfe = None

    _mfe_cache[seq20] = mfe
    return mfe


def expression_fitness(seq20: str) -> dict:
    """表达适配度三指标 + 风险标注（缺数据如实标注）。"""
    seq20 = seq20.strip().upper()
    poly_t = has_poly_t(seq20)
    g5 = starts_with_g(seq20)
    try:
        mfe = spacer_mfe(seq20)
    except ValueError:
        mfe = None
    mfe_risk = None if mfe is None else bool(mfe < MFE_RISK_THRESHOLD)
    notes = []
    if poly_t:
        notes.append("含 TTTT poly-T 终止信号（U6 转录提前终止，候选枚举阶段硬过滤）")
    if g5:
        notes.append("5' 端为 G（U6 转录起始偏好，表达加分）")
    else:
        notes.append("5' 端非 G（U6 起始偏好 G，表达可能受影响）")
    if mfe is None:
        notes.append("MFE 不可用（ViennaRNA 缺失），如实标注缺失")
    elif mfe_risk:
        notes.append(f"spacer MFE {mfe:.2f} < {MFE_RISK_THRESHOLD} kcal/mol：自折叠风险线以上，可能抑制靶向活性")
    else:
        notes.append(f"spacer MFE {mfe:.2f} ≥ {MFE_RISK_THRESHOLD} kcal/mol：自折叠风险可接受")
    notes.append("MFE 为参考维度（仅 20nt spacer 自折叠，不含 scaffold），需与 GC、脱靶、染色质状态综合判断")
    return {
        "poly_t": poly_t,
        "poly_t_filtered": poly_t,
        "five_prime_g": g5,
        "mfe_kcal": mfe,
        "mfe_risk": mfe_risk,
        "mfe_threshold": MFE_RISK_THRESHOLD,
        "note": "；".join(notes),
    }
