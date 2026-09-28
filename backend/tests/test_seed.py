import pandas as pd
import pytest
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate, GeneExpression
from backend.app.db.seed import seed_candidates_if_empty, build_expression_record
from sqlalchemy import select, func


@pytest.mark.anyio
async def test_auto_seed_loads_full_dataset():
    # 确保数据库已初始化并清空
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
        await session.execute(Gene.__table__.delete())
        await session.commit()

    # 执行从真实 demo 数据 CSV 导入
    inserted_count = await seed_candidates_if_empty()
    assert inserted_count > 0

    async with AsyncSessionLocal() as session:
        genes_cnt = await session.execute(select(func.count(Gene.gene_id)))
        # 并存方案：全基因组约 4.6 万 + demo 49 个 NLR
        assert genes_cnt.scalar() >= 49

        wide_cnt = await session.execute(
            select(func.count(Gene.gene_id)).where(Gene.gene_id.like("LsT2T%"))
        )
        assert wide_cnt.scalar() > 40000, "全基因组目录应灌入 LsT2T* 基因"

        nlr_cnt = await session.execute(
            select(func.count(Gene.gene_id)).where(Gene.gene_id.like("LsaT2T%"))
        )
        assert nlr_cnt.scalar() == 49, "49 个 NLR 代表基因应与全基因组并存"

        cands_cnt = await session.execute(select(func.count(TargetCandidate.id)))
        assert cands_cnt.scalar() > 0

    # 二次执行应跳过（幂等性）
    second_insert = await seed_candidates_if_empty()
    assert second_insert == 0


def _expr_df():
    return pd.DataFrame(
        {"Root": [10.0], "Stem": [2.0], "Leaf": [5.0], "Flower": [1.0], "Seed": [0.5]},
        index=["LSA12345"],
    )


def test_build_expression_record_mapped():
    xw = {"lsa_primary": "LSA12345", "tier": 1, "lsa_vote_frac": 0.9,
          "lsa_resolved_frac": 0.8, "n_cluster": 1}
    rec = build_expression_record("LsT2T1G000010", xw, _expr_df(), "缺 crosswalk")
    assert rec.is_mappable is True
    assert rec.lsa_id == "LSA12345"
    assert rec.tpm_root == 10.0 and rec.tpm_seed == 0.5
    assert rec.top_tissue == "根" and rec.top_tpm == 10.0
    assert rec.tau is not None and 0 <= rec.tau <= 1
    assert rec.unmappable_reason is None


def test_build_expression_record_unmappable_no_fabricated_tpm():
    # tier4 不可映射：如实标缺失，禁止编造 TPM
    xw = {"lsa_primary": None, "tier": 4, "lsa_vote_frac": 0.3,
          "lsa_resolved_frac": 0.1, "n_cluster": 0}
    rec = build_expression_record("LsT2T1G000010", xw, _expr_df(), "缺 crosswalk")
    assert rec.is_mappable is False
    assert rec.tpm_root is None and rec.tpm_leaf is None
    assert "无对应注释" in rec.unmappable_reason


def test_build_expression_record_missing_crosswalk():
    rec = build_expression_record("LsT2T1G000010", {}, _expr_df(), "缺 crosswalk")
    assert rec.is_mappable is False
    assert rec.unmappable_reason == "缺 crosswalk"
    assert rec.tpm_root is None


def test_build_expression_record_lsa_not_in_matrix():
    xw = {"lsa_primary": "LSA99999", "tier": 2, "lsa_vote_frac": 0.9,
          "lsa_resolved_frac": 0.8, "n_cluster": 1}
    rec = build_expression_record("LsT2T1G000010", xw, _expr_df(), "缺 crosswalk")
    assert rec.is_mappable is False
    assert "未收录于 5 组织表达矩阵" in rec.unmappable_reason
