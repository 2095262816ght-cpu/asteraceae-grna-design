import pytest
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate
from backend.app.db.seed import seed_candidates_if_empty
from sqlalchemy import select, func


@pytest.mark.anyio
async def test_auto_seed_loads_full_dataset():
    # 确保数据库已初始化并清空
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(Gene.__table__.delete())
        await session.commit()

    # 执行从真实 demo 数据 CSV 导入
    inserted_count = await seed_candidates_if_empty()
    assert inserted_count > 0

    async with AsyncSessionLocal() as session:
        genes_cnt = await session.execute(select(func.count(Gene.gene_id)))
        assert genes_cnt.scalar() == 49

        cands_cnt = await session.execute(select(func.count(TargetCandidate.id)))
        assert cands_cnt.scalar() == 19839

    # 二次执行应跳过（幂等性）
    second_insert = await seed_candidates_if_empty()
    assert second_insert == 0
