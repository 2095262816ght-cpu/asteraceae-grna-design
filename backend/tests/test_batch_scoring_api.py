import io
import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, ScoringJob, ScoringJobItem
from backend.app.services.batch_service import run_batch_scoring_task


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
async def test_download_templates():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. CSV 模板
        res_csv = await ac.get("/api/v1/scoring/template?format=csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert len(res_csv.content) > 100
        assert "30bp" in res_csv.content.decode("utf-8-sig")

        # 2. Excel 模板
        res_xlsx = await ac.get("/api/v1/scoring/template?format=xlsx")
        assert res_xlsx.status_code == 200
        assert "openxmlformats" in res_xlsx.headers["content-type"]
        assert len(res_xlsx.content) > 1000


@pytest.mark.anyio
async def test_batch_upload_validation_errors():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 上传不支持的后缀文件
        res_bad_ext = await ac.post(
            "/api/v1/scoring/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert res_bad_ext.status_code == 400
        assert "仅支持上传" in res_bad_ext.json()["detail"]

        # 上传空内容文件
        res_empty = await ac.post(
            "/api/v1/scoring/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert res_empty.status_code == 400


@pytest.mark.anyio
async def test_batch_upload_and_async_lifecycle():
    csv_content = (
        "靶点编号,30bp靶位点序列,说明\n"
        "G01,TTTGTGGATTCCGGTAGAATCTGATGGAAT,测试合法序列1\n"
        "G02,ATCGGCTAAGCTAGGCTAGCATCGTGGATC,测试合法序列2\n"
        "G03,INVALID_SHORT_SEQ,测试错误非法序列\n"
    ).encode("utf-8")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        upload_res = await ac.post(
            "/api/v1/scoring/upload",
            files={"file": ("candidates.csv", csv_content, "text/csv")},
        )
        assert upload_res.status_code == 202
        data = upload_res.json()
        job_id = data["job_id"]
        assert data["total_sequences"] == 3
        assert data["valid_count"] == 2
        assert data["invalid_count"] == 1
        assert data["status"] == "pending"

        # 执行后台工作任务
        await run_batch_scoring_task(job_id=job_id)

        # 轮询获取任务状态与结果明细
        job_res = await ac.get(f"/api/v1/scoring/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()

        assert job_data["status"] == "completed"
        assert job_data["total_sequences"] == 3
        assert job_data["processed_sequences"] == 3
        assert job_data["progress_pct"] == 100.0
        assert len(job_data["items"]) == 3

        # 验证合法项打分计算
        item1 = next(it for it in job_data["items"] if it["custom_id"] == "G01")
        assert item1["is_valid"] is True
        assert item1["guide_seq"] == "TGGATTCCGGTAGAATCTGA"
        assert item1["pam"] == "TGG"
        assert item1["efficiency_score"] is not None
        assert item1["gc_pct"] == 45.0

        # 验证非法项错误信息记录
        item3 = next(it for it in job_data["items"] if it["custom_id"] == "G03")
        assert item3["is_valid"] is False
        assert item3["efficiency_score"] is None
        assert item3["error_message"] is not None


@pytest.mark.anyio
async def test_get_nonexistent_job():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/scoring/jobs/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404
