"""脱靶位点评分：CFD（Doench 2016）与 MIT/Hsu（2013）特异性评分。

- CFD（Cutting Frequency Determination）单位点评分：
  错配罚分按位置与碱基对类型连乘，再乘 PAM 罚分。
  实现移植自官方 lindayqlin/CFD_score_calculator（python/cfd_score_calculator.py），
  矩阵见 cfd_score_data.py（由官方 mismatch_scores.pkl / pam_scores.pkl 转换）。
  参考文献：Doench et al., Nat Biotechnol 2016, 34:187-193.
- MIT/Hsu 单位点评分（"Scores of single hits", crispr.mit.edu）：
  三因子乘积（位置权重错配罚分 × 错配间距因子 × 错配数因子）。
  实现移植自 CRISPOR（maximilianh/crisporWebsite crispor.py: calcHitScore / calcMitGuideScore）。
  参考文献：Hsu et al., Nat Biotechnol 2013, 31:827-832.
- guide 级特异性汇总沿用 CRISPOR 口径：
  MIT: Sguide = 100/(100 + Σ hitScore) × 100（整数 0-100）；
  CFD: 10000 / Σ(cfd_site × 100)（无脱靶合计时记 100）。

口径说明：本项目脱靶扫描仅限 PAM=NGG 位点，故 PAM 罚分恒为 1.0；
CFD 差异全部来自错配位置/类型。
"""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from backend.app.services.cfd_score_data import MM_SCORES, PAM_SCORES

# Hsu 2013 位置权重矩阵 M（0-based，PAM 远端为 0）
HIT_SCORE_M = [0, 0, 0.014, 0, 0, 0.395, 0.317, 0, 0.389, 0.079,
               0.445, 0.508, 0.613, 0.851, 0.732, 0.828, 0.615, 0.804, 0.685, 0.583]

_RC_TABLE = str.maketrans("ACTUG-", "TGAAC-")


def _revcomp_nt(nt: str) -> str:
    return nt.translate(_RC_TABLE)


def cfd_site_score(spacer20: str, protospacer20: str, pam_last2: str = "GG") -> float:
    """单位点 CFD score（0-1，完全匹配 = 1.0）。

    spacer20: 20nt gRNA 引导序列（5'→3'）；
    protospacer20: 同向比对的 20nt 靶 DNA 序列；
    pam_last2: 该位点 PAM 的末 2nt（NGG 即 "GG"）。
    """
    spacer20 = spacer20.upper().replace("T", "U")
    protospacer20 = protospacer20.upper().replace("T", "U")
    pam_last2 = pam_last2.upper()
    if len(spacer20) != 20 or len(protospacer20) != 20 or len(pam_last2) != 2:
        raise ValueError("cfd_site_score 需要 20nt spacer、20nt protospacer 与 2nt PAM")
    if pam_last2 not in PAM_SCORES:
        raise ValueError(f"未知 PAM: {pam_last2}")

    score = 1.0
    for i, dna_nt in enumerate(protospacer20):
        rna_nt = spacer20[i]
        if rna_nt == dna_nt:
            continue
        key = f"r{rna_nt}:d{_revcomp_nt(dna_nt)},{i + 1}"
        score *= MM_SCORES[key]
    score *= PAM_SCORES[pam_last2]
    return score


def mit_hit_score(spacer20: str, protospacer20: str) -> float:
    """单位点 MIT/Hsu hit score（0-100；完全匹配 = 100.0）。"""
    s1, s2 = spacer20.upper(), protospacer20.upper()
    if len(s1) != 20 or len(s2) != 20:
        raise ValueError("mit_hit_score 需要 20nt spacer 与 20nt protospacer")

    max_dist = 19
    dists: List[int] = []
    mm_count = 0
    last_mm_pos = None
    score1 = 1.0
    for pos in range(20):
        if s1[pos] != s2[pos]:
            mm_count += 1
            if last_mm_pos is not None:
                dists.append(pos - last_mm_pos)
            score1 *= 1 - HIT_SCORE_M[pos]
            last_mm_pos = pos

    if mm_count < 2:
        score2 = 1.0
    else:
        avg_dist = sum(dists) / len(dists)
        score2 = 1.0 / (((max_dist - avg_dist) / float(max_dist)) * 4 + 1)

    if mm_count == 0:
        score3 = 1.0
    else:
        score3 = 1.0 / (mm_count ** 2)

    return score1 * score2 * score3 * 100


def mit_guide_score(hit_sum: float) -> int:
    """MIT guide 特异性分 Sguide = 100/(100+ΣhitScore)×100（0-100 整数）。"""
    return int(round(100 / (100 + hit_sum) * 100))


def cfd_guide_score(hit_sum_cfd: float) -> float:
    """CFD guide 特异性分（CRISPOR 口径）= 100/Σcfd_site；无脱靶合计记 100.0。

    CRISPOR 原式 10000/Σ(cfd_site×100) 与此恒等。
    """
    if hit_sum_cfd <= 0:
        return 100.0
    return 100.0 / hit_sum_cfd


def aggregate_specificity(
    spacer20: str, sites: Sequence[dict], exclude_index: int | None = None
) -> dict:
    """由单位点列表汇总 guide 级特异性。

    sites: 每项含 protospacer20 / mismatch_count；exclude_index 为视为在靶（自身）的下标。
    完全匹配位点（mismatch 0）除被排除的在靶外全部计入脱靶合计（多拷贝完全匹配是高危伪靶点）。
    """
    mit_sum = 0.0
    cfd_sum = 0.0
    n_off = 0
    for i, site in enumerate(sites):
        if exclude_index is not None and i == exclude_index:
            continue
        mit_sum += site.get("mit_hit_score") or mit_hit_score(spacer20, site["protospacer20"])
        cfd_sum += site.get("cfd_score") or cfd_site_score(spacer20, site["protospacer20"])
        n_off += 1
    return {
        "n_offtarget_sites_scored": n_off,
        "mit_hit_sum": mit_sum,
        "mit_specificity": mit_guide_score(mit_sum),
        "cfd_hit_sum": cfd_sum,
        "cfd_specificity": round(cfd_guide_score(cfd_sum), 2),
    }
