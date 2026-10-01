# -*- coding: utf-8 -*-
"""test_deep_architecture.py — 深度模块架构单元测试。

验证 /improve-codebase-architecture 演进产出的三个深度模块：
1. core.sequence_spec.SequenceSpec 领域值对象与强类型断言；
2. app.recommendation_engine.CandidateRankingEngine 推荐与多组学决策引擎；
3. app.inference_client.InferenceClient 跨环境推理接缝模块。

运行方式（grna-demo 或 crispr 环境）：
    python tests/test_deep_architecture.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
APP_DIR = BASE / "app"
for p in (str(BASE), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.sequence_spec import (
    SequenceSpec,
    validate_seq30,
    GUIDE_SLICE,
    SEED_SLICE,
    PAM_SLICE,
    PAM_N_SLICE,
)
try:
    from recommendation_engine import (
        CandidateRankingEngine,
        SORT_EFFICIENCY,
        TISSUES,
        EXPRESSION_STATUS_MAP,
    )
except ImportError:
    from app.recommendation_engine import (
        CandidateRankingEngine,
        SORT_EFFICIENCY,
        TISSUES,
        EXPRESSION_STATUS_MAP,
    )

try:
    from inference_client import (
        InferenceClient,
        BatchInferenceResult,
        SRC_LABELS,
    )
except ImportError:
    from app.inference_client import (
        InferenceClient,
        BatchInferenceResult,
        SRC_LABELS,
    )


class TestSequenceSpec:
    """测试 SequenceSpec 领域值对象与序列切片契约"""

    VALID_SEQ = "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"

    def test_valid_parsing(self):
        spec = SequenceSpec.parse(self.VALID_SEQ)
        assert spec.seq30 == self.VALID_SEQ
        assert spec.flank_5p == "ATCG"
        assert spec.guide == "GCTAAGCTAGGCTAGCATCG"
        assert spec.seed == "GCATCG"
        assert spec.pam == "TGG"
        assert spec.pam_n == "T"
        assert spec.flank_3p == "ATC"
        assert len(spec.guide) == 20
        assert len(spec.seed) == 6
        assert len(spec.pam) == 3

    def test_biophysical_features(self):
        spec = SequenceSpec.parse(self.VALID_SEQ)
        assert 0.0 <= spec.gc_total <= 1.0
        assert 0.0 <= spec.gc_seed <= 1.0
        assert spec.poly_t in (0, 1)
        assert spec.tm > 0.0

        # PAM onehot 互斥且完整
        onehot = spec.pam_onehot
        assert sum(onehot.values()) == 1.0
        assert onehot["pam_n_T"] == 1.0
        assert onehot["pam_n_A"] == 0.0

    def test_validation_errors(self):
        assert validate_seq30(self.VALID_SEQ) is None
        assert "须为 30bp" in validate_seq30("ATCG")
        assert "仅允许 A/C/G/T" in validate_seq30(self.VALID_SEQ[:29] + "N")
        assert "须为 NGG PAM" in validate_seq30(self.VALID_SEQ[:25] + "AA" + self.VALID_SEQ[27:])


class TestCandidateRankingEngine:
    """测试 CandidateRankingEngine 推荐与多组学决策引擎"""

    @classmethod
    def setup_class(cls):
        cls.engine = CandidateRankingEngine.load_from_directory(BASE)

    def test_engine_loaded_genes(self):
        assert len(self.engine.genes) == 49
        assert "LsaT2T01G023690" in self.engine.genes

    def test_ranking_default_view(self):
        res = self.engine.rank(
            gene_id="LsaT2T01G023690",
            target_tissue="Leaf",
        )
        assert len(res.top10_df) == 10
        assert len(res.all_df) > 10
        
        # 验证核心列存在
        cols = list(res.top10_df.columns)
        for fragment in ["组织优先指数（叶）", "效率分", "功能性脱靶危害（叶）", "面板内位点数", "表达证据"]:
            assert any(fragment in c for c in cols), f"缺少 {fragment} 列，现有: {cols}"

        # 验证表达证据语义化标注
        assert res.top10_df["表达证据"].iloc[0] == "已映射（串联簇）"

    def test_sorting_dispatch(self):
        # 组织优先指数排序
        res_prio = self.engine.rank("LsaT2T01G023690", "Leaf")
        top_prio = res_prio.top10_df["guide_id"].tolist()

        # 切换为纯效率分排序（按排序意图选择，不解析界面文案）
        res_eff = self.engine.rank("LsaT2T01G023690", "Leaf", sort_intent=SORT_EFFICIENCY)
        top_eff = res_eff.top10_df["guide_id"].tolist()

        # 推荐序列必须真实发生改变
        assert top_prio != top_eff, "不同排序准则下的 Top 10 应当不相同"

    def test_unmappable_gene(self):
        res = self.engine.rank("LsaT2T01G030600", "Leaf")
        assert (res.top10_df["表达证据"] == "表达证据缺失").all()


class TestInferenceClientArchitecture:
    """测试 InferenceClient 接口契约与结构化封装"""

    def test_empty_input(self):
        client = InferenceClient()
        res = client.score_sequences([])
        assert isinstance(res, BatchInferenceResult)
        assert res.total_count == 0
        assert len(res.raw_df) == 0
        assert not res.has_approximated
        assert res.warning_message is None

    def test_result_properties(self):
        import pandas as pd
        raw = pd.DataFrame({
            "seq30": ["ATCGGCTAAGCTAGGCTAGCATCGTGGATC"],
            "deepspcas9_score": [70.0],
            "crispron_source": ["wsl_real"],
            "stacking_score": [30.0],
        })
        display = raw.rename(columns={
            "seq30": "30bp 序列",
            "deepspcas9_score": "DeepSpCas9 分数",
            "crispron_source": "CRISPRon 来源",
            "stacking_score": "Stacking 集成效率分",
        })
        res = BatchInferenceResult(
            raw_df=raw,
            display_df=display,
            latency_s=1.2,
            total_count=1,
            n_approximated=0,
        )
        assert not res.has_approximated
        assert "真实模型实跑" in res.caption_message


def run_all_tests():
    test_classes = [TestSequenceSpec, TestCandidateRankingEngine, TestInferenceClientArchitecture]
    total = 0
    passed = 0
    print("=" * 60)
    print(" 正在运行深度架构重构验证套件 (test_deep_architecture.py)")
    print("=" * 60)
    for cls in test_classes:
        inst = cls()
        if hasattr(inst, "setup_class"):
            inst.setup_class()
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
    print(f" 深度架构测试完成: 全部 {passed}/{total} 项通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
