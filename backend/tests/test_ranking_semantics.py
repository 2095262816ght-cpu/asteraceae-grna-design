"""排序语义单点定义（cs_pipeline.core.ranking_semantics）与排序帮助端点。"""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from cs_pipeline.core.ranking_semantics import (
    expression_term,
    hazard_formula_text,
    penalty,
    priority_formula_text,
    priority_score,
    priority_score_atac,
    within_gene_percentiles,
)


def test_priority_score_formula_values():
    # 与历史实现逐值一致：0.50×Pct − 0.25×Pen + 0.25×S(E)，Penalty=min(1, Σw·mis/10)
    assert penalty(10, 0, 0, 0) == 1.0  # 触顶截断
    assert penalty(0, 2, 0, 0) == pytest.approx((2 * 0.5) / 10)
    assert expression_term(None) == 0.0  # 无表达证据 → 0
    assert priority_score(0.8, 0.2, 0.5) == pytest.approx(0.50 * 0.8 - 0.25 * 0.2 + 0.25 * 0.5)
    # 表观折中变体权重（0.45/0.25/0.20/0.10）同样单点定义
    assert priority_score_atac(0.8, 0.2, 0.5, 0.9) == pytest.approx(
        0.45 * 0.8 - 0.25 * 0.2 + 0.20 * 0.5 + 0.10 * 0.9
    )


def test_within_gene_percentiles_declared_interface():
    rows = [("g", 1, 10.0), ("g", 2, 20.0), ("g", 3, 30.0)]
    pct = within_gene_percentiles(rows)
    assert pct[1] == pytest.approx(1 / 3)
    assert pct[2] == pytest.approx(2 / 3)
    assert pct[3] == pytest.approx(1.0)


def test_formula_texts_render_canonical_numbers():
    # 文案数字由常量渲染，不得与实现漂移
    text = priority_formula_text()
    for fragment in ("0.5", "0.25", "min(1", "sigmoid(log2(TPM_t+1)"):
        assert fragment in text
    assert "10" in text and "2.0" in text
    assert "ω" in hazard_formula_text()


@pytest.mark.anyio
async def test_sort_help_endpoint_uses_canonical_formula_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/meta/sort-help", params={"tissue_name": "叶"})
    assert res.status_code == 200
    items = {it["key"]: it for it in res.json()["items"]}
    assert priority_formula_text() in " ".join(items["priority_score"]["lines"])
    assert "组织优先指数（叶）" in items["priority_score"]["title"]
    assert "不是 MIT/CFD 评分" in " ".join(items["offtarget_count_mis3"]["lines"])
    assert priority_formula_text() not in " ".join(items["gc_pct"]["lines"])
