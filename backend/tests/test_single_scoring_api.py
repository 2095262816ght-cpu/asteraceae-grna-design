import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, ScoringJob, ScoringJobItem
from sqlalchemy import select


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(ScoringJobItem.__table__.delete())
        await session.execute(ScoringJob.__table__.delete())
        await session.commit()
    yield


@pytest.mark.anyio
async def test_single_scoring_with_valid_sequence():
    valid_seq = "TTTGTGGATTCCGGTAGAATCTGATGGAAT"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": valid_seq, "title": "测试靶点单打分"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["seq30"] == valid_seq
    assert data["guide_seq"] == "TGGATTCCGGTAGAATCTGA"
    assert data["pam"] == "TGG"
    assert "efficiency_score" in data
    assert data["efficiency_score"] is not None
    assert "gc_pct" in data
    assert "tm_c" in data
    assert "job_id" in data

    # 验证是否成功持久化写入数据库
    async with AsyncSessionLocal() as session:
        job = await session.get(ScoringJob, data["job_id"])
        assert job is not None
        assert job.status == "completed"
        assert job.total_sequences == 1


@pytest.mark.anyio
async def test_single_scoring_with_invalid_sequence():
    # 长度不足 30bp
    invalid_seq = "ACGTACGT"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": invalid_seq},
        )

    assert response.status_code == 400
    assert "30bp" in response.json()["detail"]


@pytest.mark.anyio
async def test_single_scoring_with_invalid_pam():
    # 第 26-27 位不是 GG
    invalid_pam_seq = "TTTGTGGATTCCGGTAGAATCTGATGAAAT"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": invalid_pam_seq},
        )

    assert response.status_code == 400
    assert "NGG" in response.json()["detail"]
