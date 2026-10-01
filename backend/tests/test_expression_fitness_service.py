"""表达适配度（教师反馈 #2）：poly-T 硬过滤、5'G、spacer-only MFE。"""
from backend.app.services.expression_fitness_service import (
    MFE_RISK_THRESHOLD,
    expression_fitness,
    has_poly_t,
    spacer_mfe,
    starts_with_g,
)


def test_poly_t_detection():
    assert has_poly_t("CCCCGGGGTTTTCCCCAAAA")
    assert has_poly_t("TTTTAAAAAAAAAAAAAAAA")
    assert not has_poly_t("CCCCGGGGTTTACCCCAAAA")  # 仅 3 连 T
    assert not has_poly_t("ACGT" * 5)


def test_five_prime_g():
    assert starts_with_g("G" + "ACGT" * 4 + "ACG")
    assert not starts_with_g("A" + "ACGT" * 4 + "ACG")


def test_spacer_mfe_value_or_none():
    mfe = spacer_mfe("ACGTACGTACGTACGTACGT")
    # ViennaRNA 可用时为 float；不可用时为 None（如实缺失，不编造）
    if mfe is not None:
        assert isinstance(mfe, float)
        assert -100.0 < mfe < 100.0


def test_expression_fitness_block():
    fit = expression_fitness("CCCCGGGGTTTTCCCCAAAA")
    assert fit["poly_t"] is True
    assert fit["poly_t_filtered"] is True
    assert fit["mfe_threshold"] == MFE_RISK_THRESHOLD
    assert "TTTT" in fit["note"]

    fit2 = expression_fitness("G" + "ACGT" * 4 + "ACG")
    assert fit2["five_prime_g"] is True
    assert fit2["poly_t"] is False
    if fit2["mfe_kcal"] is not None:
        assert fit2["mfe_risk"] == (fit2["mfe_kcal"] < MFE_RISK_THRESHOLD)
