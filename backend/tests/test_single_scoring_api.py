import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, OfftargetProfileCache, ScoringJob, ScoringJobItem
from backend.app.services import scoring_service
from backend.tests.stub_inference import StubInferenceClient
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
async def test_single_scoring_with_valid_sequence(monkeypatch):
    # 模型不可用：效率分如实标缺失，不以启发式公式编造（口径纪律「不硬猜」）
    monkeypatch.setattr(scoring_service, "_HAS_INFERENCE_CLIENT", False)
    valid_seq = "TTTGTGGATTCCGGTAGAATCTGATGGAAT"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": valid_seq, "title": "测试靶点单打分", "bundle_id": "tks"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["seq30"] == valid_seq
    assert data["guide_seq"] == "TGGATTCCGGTAGAATCTGA"
    assert data["pam"] == "TGG"
    assert data["efficiency_score"] is None
    assert data["crispron_source"] is None
    assert "未计算" in (data["warning_message"] or "")
    assert "gc_pct" in data
    assert "tm_c" in data

    # 验证是否成功持久化写入数据库（含任务记录的参考包，历史导出缺省沿用）
    async with AsyncSessionLocal() as session:
        job = await session.get(ScoringJob, data["job_id"])
        assert job is not None
        assert job.status == "completed"
        assert job.total_sequences == 1
        assert job.bundle_id == "tks"


@pytest.mark.anyio
async def test_single_scoring_uses_model_scores_when_available(monkeypatch):
    # 有模型分：efficiency/CRISPRon 分与来源如实透传（CrispronScorer 不变量）
    stub = StubInferenceClient(
        [{
            "deepspcas9_score": 66.6,
            "crispron_score": 77.7,
            "crispron_source": "wsl_real",
            "stacking_score": 81.25,
        }]
    )
    monkeypatch.setattr(scoring_service, "_HAS_INFERENCE_CLIENT", True)
    monkeypatch.setattr(scoring_service, "InferenceClient", lambda: stub)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": "TTTGTGGATTCCGGTAGAATCTGATGGAAT", "title": "模型分透传"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["efficiency_score"] == pytest.approx(81.25)
    assert data["deepspcas9_score"] == pytest.approx(66.6)
    assert data["crispron_score"] == pytest.approx(77.7)
    assert data["crispron_source"] == "wsl_real"


@pytest.mark.anyio
async def test_single_scoring_with_invalid_sequence():
    # 长度不足 30bp
    invalid_seq = "ACGTACGT"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": invalid_pam_seq},
        )

    assert response.status_code == 400
    assert "NGG" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_scoring_job_cascades_items_keeps_computed_data():
    # 删作业：连带逐条序列明细；已算好的脱靶持久化结果保留
    async with AsyncSessionLocal() as session:
        await session.execute(OfftargetProfileCache.__table__.delete())
        session.add(ScoringJob(id="del-job-1", title="待删作业", job_type="single", status="completed",
                               total_sequences=1, processed_sequences=1))
        session.add(ScoringJobItem(job_id="del-job-1", seq30="TTTGTGGATTCCGGTAGAATCTGATGGAAT", is_valid=True))
        session.add(OfftargetProfileCache(genome_key="g.fa", seq20="TGGATTCCGGTAGAATCTGA",
                                          exact=1, mis1=1, mis2=2, mis3=3))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete("/api/v1/scoring/jobs/del-job-1")
        assert res.status_code == 200
        res_404 = await ac.delete("/api/v1/scoring/jobs/del-job-1")
        assert res_404.status_code == 404

    async with AsyncSessionLocal() as session:
        assert (await session.get(ScoringJob, "del-job-1")) is None
        items = (await session.execute(select(ScoringJobItem).where(ScoringJobItem.job_id == "del-job-1"))).scalars().all()
        assert items == []
        # 算好的数据不动
        profs = (await session.execute(select(OfftargetProfileCache))).scalars().all()
        assert len(profs) == 1 and profs[0].mis3 == 3
