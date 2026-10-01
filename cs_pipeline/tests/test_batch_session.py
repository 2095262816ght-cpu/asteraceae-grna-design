# -*- coding: utf-8 -*-
"""BatchScoringSession（批量打分生命周期深度模块）单元测试。

只穿过模块接口验证：防碰撞缓存键、动态超时策略、结果拼装、ATAC 展示转换。
推理客户端用桩替代，零 Streamlit 依赖。

在 cs_pipeline/ 目录下运行（crispr 或 grna-demo 环境）：
    python tests/test_batch_session.py
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

BASE = Path(__file__).resolve().parents[1]
APP_DIR = BASE / "app"
for p in (str(BASE), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from batch_session import BatchScoringSession  # noqa: E402
from core.atac_annotator import peaks_from_dataframe  # noqa: E402
from inference_client import BatchInferenceResult  # noqa: E402

SEQ_OK = "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"
SEQ_BAD = "ATCG"  # 长度非法


class _StubClient:
    def __init__(self):
        self.calls = []

    def score_sequences(self, seqs, timeout_s=None):
        seqs = list(seqs)
        self.calls.append((seqs, timeout_s))
        raw = pd.DataFrame({
            "seq30": seqs,
            "deepspcas9_score": [0.8] * len(seqs),
            "crispron_score": [50.0] * len(seqs),
            "crispron_source": ["wsl_real"] * len(seqs),
            "stacking_score": [60.0] * len(seqs),
        })
        return BatchInferenceResult(
            raw_df=raw, display_df=raw.copy(), latency_s=0.1, total_count=len(seqs), n_approximated=0
        )


def _session(id_col=None):
    return BatchScoringSession(
        file_bytes=b"fake-bytes", filename="t.xlsx", sheet_name="Sheet1",
        seq_col="seq30", id_col=id_col,
    )


def _raw_df():
    return pd.DataFrame({"seq30": [SEQ_OK, SEQ_BAD], "gene": ["G1", "G2"]})


def test_cache_key_composition_and_discrimination():
    s1 = _session(id_col="gene")
    s2 = _session(id_col="gene")
    s3 = _session(id_col=None)
    assert s1.cache_key == s2.cache_key
    assert s1.cache_key != s3.cache_key
    other = BatchScoringSession(b"other-bytes", "t.xlsx", "Sheet1", "seq30", "gene")
    assert other.cache_key != s1.cache_key


def test_run_passes_dynamic_timeout_policy():
    # 策略内聚在模块里：固定下限 + 随条数线性放宽
    sess = _session()
    pre = sess.precheck(_raw_df())
    client = _StubClient()
    sess.run(_raw_df(), pre, client)
    assert client.calls[0][1] == max(180, len(pre.valid_sequences) * 5 + 60)

    big_df = pd.DataFrame({"seq30": [SEQ_OK] * 100})
    big_sess = _session()
    big_pre = big_sess.precheck(big_df)
    big_client = _StubClient()
    big_sess.run(big_df, big_pre, big_client)
    assert big_client.calls[0][1] == 100 * 5 + 60


def test_run_merges_results_row_aligned():
    sess = _session()
    raw = _raw_df()
    pre = sess.precheck(raw)
    assert pre.valid_count == 1 and pre.invalid_count == 1
    infer_res, merged = sess.run(raw, pre, _StubClient())
    assert infer_res.total_count == 1
    assert merged.loc[0, "检测状态"] == "检测成功"
    assert merged.loc[0, "Stacking 集成效率分"] == 60.0
    assert str(merged.loc[1, "检测状态"]).startswith("格式异常")
    assert merged.loc[1, "Stacking 集成效率分"] == "-"


def test_annotate_atac_returns_display_shaped_result():
    atlas = peaks_from_dataframe(pd.DataFrame({
        "chrom": ["Chr1"], "start": [100], "end": [200], "fold_change": [10.0],
    }))
    merged = pd.DataFrame({
        "seq30": [SEQ_OK], "chrom": ["Chr1"], "start": [120], "end": [149],
    })
    atac = _session().annotate_atac(merged, atlas, "chrom", "start", "end")
    assert atac.n_in_peak == 1
    assert "ATAC状态" in atac.display_df.columns
    assert "ATAC开放峰内" in atac.display_df.columns
    assert atac.display_df["ATAC开放峰内"].tolist() == ["是"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
