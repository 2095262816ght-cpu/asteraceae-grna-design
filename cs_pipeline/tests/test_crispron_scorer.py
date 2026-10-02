# -*- coding: utf-8 -*-
"""CrispronScorer（CRISPRon 来源裁决模块）单元测试。

只穿过模块接口验证，全部用桩 runner，不触碰 WSL/TF 栈：
真实模型优先、逐条降级标注、近似式单一定义、批量口径全标注、线格式标签不变量。

在 cs_pipeline/ 目录下运行（crispr 环境）：
    python tests/test_crispron_scorer.py
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.crispron_scorer import (  # noqa: E402
    COLUMNS,
    SOURCE_APPROXIMATED,
    SOURCE_WSL_REAL,
    CrispronScorer,
    no_real_runner,
)

SEQ_A = "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"
SEQ_B = "ATTCGGCGTTAGATTGACAGAAGACGGTGG"


def _features():
    deep = pd.Series([0.8, 0.4])
    tm = pd.Series([60.0, 40.0])
    return deep, tm


def test_real_runner_wins_and_labels_wsl_real():
    runner = lambda seqs: {SEQ_A: 59.61, SEQ_B: 42.0}  # noqa: E731
    out = CrispronScorer(real_runner=runner).score([SEQ_A, SEQ_B], *_features())
    assert list(out.columns) == COLUMNS
    assert out["crispron_score"].tolist() == [59.61, 42.0]
    assert out["crispron_source"].tolist() == [SOURCE_WSL_REAL, SOURCE_WSL_REAL]


def test_partial_degradation_labels_per_row():
    runner = lambda seqs: {SEQ_A: 59.61}  # noqa: E731
    out = CrispronScorer(real_runner=runner).score([SEQ_A, SEQ_B], *_features())
    assert out["crispron_source"].tolist() == [SOURCE_WSL_REAL, SOURCE_APPROXIMATED]
    assert out.loc[1, "crispron_score"] == pytest.approx(0.4 * 0.95 + (40.0 - 50.0) * 0.25)


def test_bulk_policy_labels_all_approximated():
    out = CrispronScorer(real_runner=no_real_runner).score([SEQ_A, SEQ_B], *_features())
    assert out["crispron_source"].tolist() == [SOURCE_APPROXIMATED] * 2


def test_approx_formula_single_home():
    deep, tm = _features()
    out = CrispronScorer(real_runner=no_real_runner).score([SEQ_A, SEQ_B], deep, tm)
    expected = (deep * 0.95 + (tm - 50.0) * 0.25).round(2)
    assert out["crispron_score"].tolist() == expected.tolist()


def test_index_alignment_with_feature_frames():
    deep, tm = _features()
    deep.index = ["row-7", "row-9"]
    tm.index = ["row-7", "row-9"]
    out = CrispronScorer(real_runner=no_real_runner).score([SEQ_A, SEQ_B], deep, tm)
    assert out.index.tolist() == ["row-7", "row-9"]


def test_runner_receives_normalized_seqs():
    seen = {}

    def runner(seqs):
        seen["seqs"] = seqs
        return {}

    CrispronScorer(real_runner=runner).score([f" {SEQ_A.lower()} "], pd.Series([0.8]), pd.Series([60.0]))
    assert seen["seqs"] == [SEQ_A]


def test_empty_input_returns_empty_frame():
    out = CrispronScorer(real_runner=no_real_runner).score([], pd.Series(dtype=float), pd.Series(dtype=float))
    assert list(out.columns) == COLUMNS
    assert out.empty


def test_source_labels_are_wire_format_invariants():
    # 子进程 CSV 协议、历史数据库行、前端展示映射都按这两个字面值对接，不得漂移
    assert SOURCE_WSL_REAL == "wsl_real"
    assert SOURCE_APPROXIMATED == "approximated"


def run_all_tests():
    test_funcs = [
        test_real_runner_wins_and_labels_wsl_real,
        test_partial_degradation_labels_per_row,
        test_bulk_policy_labels_all_approximated,
        test_approx_formula_single_home,
        test_index_alignment_with_feature_frames,
        test_runner_receives_normalized_seqs,
        test_empty_input_returns_empty_frame,
        test_source_labels_are_wire_format_invariants,
    ]
    print("=" * 60)
    print(" 正在运行 CRISPRon 来源裁决测试套件 (test_crispron_scorer.py)")
    print("=" * 60)
    passed = 0
    for fn in test_funcs:
        fn()
        print(f"  [PASS] {fn.__name__}")
        passed += 1
    print("=" * 60)
    print(f" CRISPRon 来源裁决测试完成: 全部 {passed}/{len(test_funcs)} 项通过！")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        run_all_tests()
    else:
        sys.exit(pytest.main([__file__, "-v"]))
