# -*- coding: utf-8 -*-
"""test_atac_annotator.py — ATAC-seq 染色质开放峰注释与表观加权排序测试。

验证：
1. peaks_from_dataframe 长表聚合去重与列名归一化（LettuceGDB 口径）；
2. annotate_guides 区间匹配（峰内/峰近端/远离/无坐标）与可及性分口径；
3. detect_coord_columns 坐标列智能探测；
4. load_default_atac 内置莴苣峰表装载（文件缺失时优雅降级）；
5. CandidateRankingEngine ATAC 注释列展示与「组织优先指数+ATAC加权」排序；
6. load_from_directory 保留 ATAC 公式所需列（eff_percentile/offtarget_penalty）。
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
for p in (str(BASE), str(BASE / "app")):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.atac_annotator import (
    COL_DIST,
    COL_FC,
    COL_IN_PEAK,
    COL_PEAK_ID,
    COL_SCORE,
    COL_STATUS,
    DISPLAY_MAP as ATAC_DISPLAY_MAP,
    STATUS_FAR,
    STATUS_IN_PEAK,
    STATUS_NEAR,
    STATUS_NO_EVIDENCE,
    annotate_guides,
    detect_coord_columns,
    load_default_atac,
    peaks_from_dataframe,
)
from recommendation_engine import CandidateRankingEngine

ATAC_XLSX = BASE / "data" / "reference_genomes" / "1-3_Stem_lettuce_ATAC_peaks.xlsx"


def _atlas():
    # peak_A 长表两行（多 gene/effect 注释），应聚合为一个区间
    peaks = pd.DataFrame({
        "Peak": ["peak_A", "peak_A", "peak_B"],
        "Chr": ["Chr01", "Chr01", "Chr02"],
        "Start": [1000, 1000, 5000],
        "End": [2000, 2000, 5200],
        "FoldChange": [8.0, 8.0, 2.0],
        "-log10(q-value)": [12.0, 12.0, 5.0],
        "gene": ["LSA1", "LSA2", "LSA3"],
        "Effect type": ["promoter", "exon", "intron"],
    })
    return peaks_from_dataframe(peaks)


def test_peaks_from_dataframe_dedup_long_table():
    atlas = _atlas()
    assert atlas.n_peaks == 2, atlas.peaks
    row = atlas.peaks[atlas.peaks.peak_id == "peak_A"].iloc[0]
    assert row["gene"] == "LSA1,LSA2"
    assert row["effect_type"] == "exon,promoter"
    assert row["fold_change"] == 8.0
    assert set(atlas.chroms) == {"Chr01", "Chr02"}


def test_annotate_guides_in_peak_near_far():
    atlas = _atlas()
    guides = pd.DataFrame({
        "guide_id": ["g_in", "g_near", "g_far"],
        "chrom": ["Chr01", "Chr01", "Chr01"],
        "start": [1200, 2480, 40000],
        "end": [1222, 2502, 40022],
    })
    out = annotate_guides(guides, atlas)

    # 峰内：距离 0，取强度 8.0 → 0.6 + 0.4*0.8 = 0.92
    assert out.loc[0, COL_IN_PEAK]
    assert out.loc[0, COL_STATUS] == STATUS_IN_PEAK
    assert out.loc[0, COL_PEAK_ID] == "peak_A"
    assert out.loc[0, COL_DIST] == 0
    assert out.loc[0, COL_FC] == 8.0
    assert out.loc[0, COL_SCORE] == pytest.approx(0.92)

    # 峰近端：guide 中心 2491 距峰中心 1500 = 991bp ≤ 5kb → 线性衰减
    assert not out.loc[1, COL_IN_PEAK]
    assert out.loc[1, COL_STATUS] == STATUS_NEAR
    assert out.loc[1, COL_DIST] == 991
    assert out.loc[1, COL_SCORE] == pytest.approx(0.3 * (1 - 991 / 5000))

    # 远离：距最近峰 38511bp，无开放证据
    assert not out.loc[2, COL_IN_PEAK]
    assert out.loc[2, COL_STATUS] == STATUS_FAR
    assert out.loc[2, COL_SCORE] == 0.0


def test_annotate_guides_no_coords():
    out = annotate_guides(pd.DataFrame({"guide_id": ["g1"], "seq20": ["A" * 20]}), _atlas())
    assert out.loc[0, COL_STATUS] == STATUS_NO_EVIDENCE
    assert out.loc[0, COL_SCORE] == 0.0
    assert out.loc[0, COL_PEAK_ID] is None


def test_detect_coord_columns():
    assert detect_coord_columns(pd.DataFrame(columns=["Chr", "Start", "End", "seq30"])) == ("Chr", "Start", "End")
    assert detect_coord_columns(pd.DataFrame(columns=["seq30", "guide_id"])) == (None, None, None)


@pytest.mark.skipif(not ATAC_XLSX.exists(), reason="内置莴苣 ATAC 峰表未落地")
def test_load_default_atac_lettuce():
    atlas = load_default_atac(BASE)
    assert atlas is not None
    assert atlas.n_peaks > 0
    assert "Chr01" in atlas.chroms


def test_load_default_atac_missing_degrades():
    assert load_default_atac(BASE / "nonexistent_dir") is None


def _engine(atlas):
    genes = pd.DataFrame({
        "gene_id": ["G1"],
        "g_chrom": ["Chr01"], "g_start": [1000], "g_end": [3000],
        "g_strand": ["+"], "nlr_type": ["—"],
    })
    cand = pd.DataFrame({
        "guide_id": ["g1", "g2", "g3"],
        "gene_id": ["G1"] * 3,
        "chrom": ["Chr01"] * 3,
        "start": [1200, 2480, 40000],
        "end": [1222, 2502, 40022],
        "strand": ["+"] * 3,
        "seq20": ["A" * 20] * 3,
        "pam": ["AGG"] * 3,
        "region_type": ["promoter"] * 3,
        "gc_pct": [50.0] * 3,
        "tm_c": [60.0] * 3,
        "efficiency_score": [0.9] * 3,
    })
    prio = pd.DataFrame({
        "guide_id": ["g1", "g2", "g3"],
        "eff_percentile": [0.5, 0.5, 0.55],
        "offtarget_penalty": [0.1] * 3,
        "expr_sigmoid_stem": [0.5] * 3,
        "priority_score_stem": [0.35, 0.35, 0.375],
    })
    return CandidateRankingEngine(cand, genes, prio, atac_atlas=atlas)


def test_engine_atac_annotation_columns_shown():
    engine = _engine(_atlas())
    assert engine.has_atac
    result = engine.rank("G1", target_tissue="Stem", region_types=("promoter",), hide_centromere=False)
    for col in ("ATAC状态", "ATAC开放峰内", "ATAC峰ID", "ATAC距峰中心(bp)", "ATAC峰强度FC", "ATAC可及性分"):
        assert col in result.all_df.columns, f"缺少 {col}；现有 {list(result.all_df.columns)}"
    assert set(result.all_df["ATAC开放峰内"]) <= {"是", "否"}
    assert result.all_df.loc[result.all_df.guide_id == "g1", "ATAC状态"].item() == STATUS_IN_PEAK
    assert result.all_df.loc[result.all_df.guide_id == "g3", "ATAC状态"].item() == STATUS_FAR


def test_engine_atac_weighted_sort_reorders():
    engine = _engine(_atlas())
    opts = engine.get_sort_options("Stem")
    atac_opt = next((o for o in opts if o.startswith("组织优先指数+ATAC")), None)
    assert atac_opt is not None, opts

    base = engine.rank("G1", target_tissue="Stem", region_types=("promoter",), hide_centromere=False)
    assert base.all_df["guide_id"].iloc[0] == "g3", "默认方案3 排序应由 priority_score 决定"

    weighted = engine.rank(
        "G1", target_tissue="Stem", sort_key=atac_opt, region_types=("promoter",), hide_centromere=False
    )
    # ATAC 开放峰内的 g1 应反超默认第一的 g3（远离峰）
    assert weighted.all_df["guide_id"].iloc[0] == "g1", weighted.all_df[["guide_id", "ATAC状态"]]
    assert "组织优先指数+ATAC（茎）" in weighted.all_df.columns
    # 默认排序的组织优先指数列不受污染
    assert "组织优先指数（茎）" in weighted.all_df.columns


def test_load_from_directory_keeps_formula_columns():
    engine = CandidateRankingEngine.load_from_directory(BASE)
    for col in ("eff_percentile", "offtarget_penalty"):
        assert col in engine._data.columns, f"{col} 被装载过滤，ATAC 加权排序将失效"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
