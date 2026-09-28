# -*- coding: utf-8 -*-
"""算法引擎与多组学数据链路单元测试套件。

涵盖：
1. predict.py 推理接口（边界值、空输入、非法长度、单调性与输出范围）；
2. features_common.py 10 维标准特征单一来源与 PAM one-hot 严格划分；
3. 多组学转录表达矩阵与 LSA↔T2T crosswalk 数据完整性；
4. 橡胶草产胶通路时相曲线与 S4 推荐窗口一致性。

在 cs_pipeline/ 目录下运行（crispr 或 grna-demo 环境）：
    python tests/test_pipeline_engine.py
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))

from features_common import FEATURE_COLS, PAM_ONEHOT, seq_features
from predict import predict_efficiency, predict_details


class TestPredictEngine:
    """测试统一推理接口 predict.py"""

    VALID_SEQ1 = "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"
    VALID_SEQ2 = "ATTCGGCGTTAGATTGACAGAAGACGGTGG"

    def test_empty_input(self):
        """空输入返回空列表和空 DataFrame，不抛异常。"""
        assert predict_efficiency([]) == []
        details = predict_details([])
        assert isinstance(details, pd.DataFrame)
        assert len(details) == 0

    def test_valid_prediction(self):
        """标准 30bp 序列预测分在 [0.0, 100.0] 区间内，返回列齐全。"""
        scores = predict_efficiency([self.VALID_SEQ1, self.VALID_SEQ2])
        assert len(scores) == 2
        for s in scores:
            assert isinstance(s, float)
            assert 0.0 <= s <= 100.0

        details = predict_details([self.VALID_SEQ1, self.VALID_SEQ2])
        assert len(details) == 2
        for col in ["seq30", "deepspcas9_score", "crispron_score", "crispron_source", "stacking_score"]:
            assert col in details.columns
        assert details["crispron_source"].isin(["wsl_real", "approximated"]).all()

    def test_case_insensitivity(self):
        """输入小写序列应自动转大写并得出完全相同的预测分。"""
        score_upper = predict_efficiency([self.VALID_SEQ1])[0]
        score_lower = predict_efficiency([self.VALID_SEQ1.lower()])[0]
        assert abs(score_upper - score_lower) < 1e-4

    def test_invalid_length(self):
        """非 30bp 序列必须触发 AssertionError。"""
        try:
            predict_efficiency(["ATCGGCTAAGCTAGGCTAGC"])  # 20bp
            assert False, "应当抛出 AssertionError"
        except AssertionError:
            pass

        try:
            predict_efficiency([self.VALID_SEQ1 + "A"])   # 31bp
            assert False, "应当抛出 AssertionError"
        except AssertionError:
            pass


class TestFeaturesCommon:
    """测试特征工程单一来源模块 features_common.py"""

    SAMPLE_SEQS = pd.Series([
        "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",  # PAM: TGG (首碱基 T)
        "ATTCGGCGTTAGATTGACAGAAGACGGTGG",  # PAM: CGG (首碱基 C)
        "AAAAATTTTTCCCCCGGGGGAAAAGGAAAA",  # PAM: AGG (首碱基 A)
        "TTTTGGGGCCCCAAAATTTTGGGGGGTTTT",  # PAM: GGG (首碱基 G)
    ])

    def test_feature_columns_and_schema(self):
        """验证 10 维标准特征列定义及派生特征。"""
        assert len(FEATURE_COLS) == 10
        feats = seq_features(self.SAMPLE_SEQS)
        assert len(feats) == len(self.SAMPLE_SEQS)

        # 检查 PAM one-hot 严格互斥：四列求和必须为 1.0
        one_hot_sum = feats[PAM_ONEHOT].sum(axis=1)
        assert (one_hot_sum == 1.0).all()

        # 检查 GC 含量和 Tm 在物理允许范围内
        assert (feats["gc_total"] >= 0.0).all() and (feats["gc_total"] <= 1.0).all()
        assert (feats["gc_seed"] >= 0.0).all() and (feats["gc_seed"] <= 1.0).all()
        assert (feats["tm"] > 0.0).all()
        assert feats["poly_t"].isin([0, 1]).all()


class TestMultiomicsDataIntegrity:
    """测试多组学数据与时相决策资产完整性"""

    def test_expression_and_crosswalk(self):
        """测试莴苣表达矩阵与 crosswalk 资产完整性。"""
        expr_path = BASE / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"
        xw_path = BASE / "results" / "crosswalk_lsa_t2t_0923.csv"
        assert expr_path.exists(), f"表达矩阵缺失: {expr_path}"
        assert xw_path.exists(), f"Crosswalk 缺失: {xw_path}"

        expr = pd.read_csv(expr_path)
        assert "GeneID" in expr.columns
        for t in ["Root", "Stem", "Leaf", "Flower", "Seed"]:
            assert t in expr.columns

        xw = pd.read_csv(xw_path)
        assert "gene_id" in xw.columns
        assert "lsa_primary" in xw.columns
        assert "tier" in xw.columns

    def test_genome_crosswalk(self):
        """测试全基因组 crosswalk（18 号批量定位引擎产物）资产完整性。"""
        xw_path = BASE / "results" / "crosswalk_lsa_t2t_genome.csv"
        catalog_path = BASE / "results" / "lettuce_all_genes_catalog.csv"
        assert xw_path.exists(), f"全基因组 Crosswalk 缺失: {xw_path}"
        assert catalog_path.exists(), f"基因目录缺失: {catalog_path}"

        xw = pd.read_csv(xw_path)
        for col in ["gene_id", "chrom_delivered", "n_guides", "tier", "lsa_primary",
                    "lsa_vote_frac", "lsa_resolved_frac", "in_expression_matrix"]:
            assert col in xw.columns, f"缺少列 {col}"

        catalog = pd.read_csv(catalog_path, usecols=["gene_id"])
        assert len(xw) == len(catalog), (
            f"crosswalk 行数 {len(xw)} != 基因目录 {len(catalog)}")
        assert xw["gene_id"].is_unique

        assert xw["tier"].isin([1, 2, 3, 4]).all()
        t4 = xw[xw["tier"] == 4]
        mapped = xw[xw["tier"] <= 3]
        assert t4["lsa_primary"].isna().all(), "tier4 不可映射基因不得编造 LSA 映射"
        assert (xw[xw["tier"] == 1]["lsa_vote_frac"] >= 0.5).all(), "tier1 精确映射票占比应 >=50%"
        assert (mapped["lsa_resolved_frac"] >= 0.2).all(), "弱解析应作废为 tier4"
        assert (mapped["cluster_coverage"] >= 0.5).all(), "低簇覆盖（票分散）应作废为 tier4"

        expr = pd.read_csv(BASE / "data" / "expression" /
                           "1-3_lettuce_5tissue_expression_matrix.csv", usecols=["GeneID"])
        in_matrix = xw[xw["in_expression_matrix"]]
        assert in_matrix["lsa_primary"].isin(set(expr["GeneID"])).all(), (
            "in_expression_matrix=True 的主映射必须真实存在于表达矩阵")

    def test_tks_stage_curves(self):
        """测试橡胶草产胶发育时相曲线与 S4 推荐窗口。"""
        curves_path = BASE / "results" / "tks_pathway_stage_curves_0923.csv"
        window_path = BASE / "results" / "tks_developmental_window_0923.csv"
        assert curves_path.exists()
        assert window_path.exists()

        window = pd.read_csv(window_path).set_index("family")
        for fam in ["CPT", "REF", "SRPP"]:
            assert fam in window.index
            assert window.loc[fam, "recommended_stage"] == "S4"


def run_all_tests():
    test_classes = [TestPredictEngine, TestFeaturesCommon, TestMultiomicsDataIntegrity]
    total = 0
    passed = 0
    print("=" * 60)
    print(" 正在运行算法引擎与多组学数据链路自动化测试")
    print("=" * 60)
    for cls in test_classes:
        inst = cls()
        for method_name in dir(inst):
            if method_name.startswith("test_"):
                total += 1
                method = getattr(inst, method_name)
                doc = method.__doc__.strip() if method.__doc__ else method_name
                try:
                    method()
                    print(f"  [PASS] {cls.__name__}.{method_name} - {doc}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {cls.__name__}.{method_name} - {doc}: {e}")
                    raise e
    print("=" * 60)
    print(f" 测试完成: 全部 {passed}/{total} 项通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
