"""CFD / MIT 脱靶评分：对照官方 doctest 数值回归。"""
from backend.app.services.cfd_score import (
    aggregate_specificity,
    cfd_guide_score,
    cfd_site_score,
    mit_guide_score,
    mit_hit_score,
)


def test_cfd_matches_official_doctests():
    # crispor.py calcCfdScore doctest（23nt = 20nt guide + PAM）
    assert abs(cfd_site_score("ATGGTCGGACTCCCTGCCAG", "ATGGTGGGACTCCCTGCCAG", "GG") - 0.5) < 1e-9
    assert abs(cfd_site_score("ATGGTCGGACTCCCTGCCAG", "ATGATCCAAATCCCTGCCAG", "GG") - 0.53625000020625) < 1e-9
    assert abs(cfd_site_score("ATGTGGAGATTGCCACCTAC", "ATCTGGAGATTGCCACCTAC", "GG") - 0.384615385) < 1e-9
    assert cfd_site_score("A" * 20, "A" * 20, "GG") == 1.0


def test_mit_hit_score():
    # 完全匹配 = 100
    assert mit_hit_score("ACGT" * 5, "ACGT" * 5) == 100.0
    # 单错配位于 0-based 位置 5（权重 0.395）：(1-0.395) × 1/1² × 100 = 60.5
    s1 = "ACGTACGTACGTACGTACGT"
    s2 = s1[:5] + "A" + s1[6:]
    assert abs(mit_hit_score(s1, s2) - 60.5) < 1e-9


def test_guide_aggregation():
    # MIT: Sguide = 100/(100+Σ)×100
    assert mit_guide_score(100.0) == 50
    assert mit_guide_score(0.0) == 100
    # CFD: 100/Σcfd_site；无脱靶记 100
    assert cfd_guide_score(0.0) == 100.0
    assert abs(cfd_guide_score(1.0) - 100.0) < 1e-9
    assert abs(cfd_guide_score(2.0) - 50.0) < 1e-9

    sites = [
        {"protospacer20": "A" * 20, "mismatch_count": 0},  # 在靶（排除）
        {"protospacer20": "C" + "A" * 19, "mismatch_count": 1},
    ]
    agg = aggregate_specificity("A" * 20, sites, exclude_index=0)
    assert agg["n_offtarget_sites_scored"] == 1
    # CFD 特异性 = 100/Σcfd（CRISPOR 口径），单个弱脱靶时可 >100
    assert agg["cfd_specificity"] > 0
    assert 0 < agg["mit_specificity"] <= 100
