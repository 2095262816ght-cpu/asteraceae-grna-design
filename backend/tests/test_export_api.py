import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate, ExportBatch, ScoringJob


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(ExportBatch.__table__.delete())
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(Gene.__table__.delete())
        await session.execute(ScoringJob.__table__.delete())

        # 插入测试基因与候选
        gene = Gene(
            gene_id="TEST_GENE_01",
            chrom="chr1",
            start=1000,
            end=5000,
            strand="+",
            candidate_count=2,
        )
        session.add(gene)

        c1 = TargetCandidate(
            id=101,
            guide_id="guide_101",
            gene_id="TEST_GENE_01",
            chrom="chr1",
            start=1200,
            end=1230,
            strand="+",
            seq30="TTTGTGGATTCCGGTAGAATCTGATGGAAT",
            seq20="TGGATTCCGGTAGAATCTGA",
            pam="TGG",
            gc_pct=45.0,
            tm_c=69.0,
            efficiency_score=85.2,
            deepspcas9_score=75.0,
            crispron_score=82.0,
            is_exon=True,
            is_centromere=False,
        )
        c2 = TargetCandidate(
            id=102,
            guide_id="guide_102",
            gene_id="TEST_GENE_01",
            chrom="chr1",
            start=1500,
            end=1530,
            strand="-",
            seq30="ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
            seq20="GCTAAGCTAGGCTAGCATCG",
            pam="TGG",
            gc_pct=50.0,
            tm_c=72.0,
            efficiency_score=68.4,
            deepspcas9_score=60.0,
            crispron_score=65.0,
            is_exon=False,
            is_centromere=False,
        )
        session.add_all([c1, c2])

        # 插入测试打分作业
        job = ScoringJob(
            id="test-job-01",
            title="历史作业1",
            job_type="single",
            status="completed",
            total_sequences=1,
            processed_sequences=1,
        )
        session.add(job)

        await session.commit()
    yield


@pytest.mark.anyio
async def test_create_export_batch_validation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 空候选列表
        res_empty = await ac.post(
            "/api/v1/exports",
            json={"name": "空批次", "format": "csv", "candidate_ids": []},
        )
        assert res_empty.status_code == 422  # pydantic min_length validation

        # 不存在的候选
        res_not_found = await ac.post(
            "/api/v1/exports",
            json={"name": "不存在", "format": "csv", "candidate_ids": [9999]},
        )
        assert res_not_found.status_code == 404


@pytest.mark.anyio
async def test_export_batch_creation_and_download():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. 创建 CSV 导出批次
        create_res = await ac.post(
            "/api/v1/exports",
            json={
                "name": "TEST_GENE_优选方案",
                "format": "csv",
                "candidate_ids": [101, 102],
                "gene_id": "TEST_GENE_01",
            },
        )
        assert create_res.status_code == 201
        data = create_res.json()
        batch_id = data["id"]
        assert data["candidate_count"] == 2
        assert data["name"] == "TEST_GENE_优选方案"

        # 2. 获取批次列表
        list_res = await ac.get("/api/v1/exports")
        assert list_res.status_code == 200
        batches = list_res.json()
        assert len(batches) >= 1
        assert any(b["id"] == batch_id for b in batches)

        # 3. 下载 CSV 文件
        dl_res = await ac.get(f"/api/v1/exports/{batch_id}/download")
        assert dl_res.status_code == 200
        assert "text/csv" in dl_res.headers["content-type"]
        assert "attachment" in dl_res.headers["content-disposition"]
        csv_text = dl_res.content.decode("utf-8-sig")
        assert "30bp完整靶位点" in csv_text
        assert "TEST_GENE_01" in csv_text
        assert "85.2" in csv_text

        # 4. 创建并下载 Excel 导出批次
        create_res_xlsx = await ac.post(
            "/api/v1/exports",
            json={
                "name": "TEST_GENE_Excel方案",
                "format": "xlsx",
                "candidate_ids": [101],
            },
        )
        assert create_res_xlsx.status_code == 201
        batch_id_xlsx = create_res_xlsx.json()["id"]

        dl_res_xlsx = await ac.get(f"/api/v1/exports/{batch_id_xlsx}/download")
        assert dl_res_xlsx.status_code == 200
        assert "openxmlformats" in dl_res_xlsx.headers["content-type"]
        assert len(dl_res_xlsx.content) > 1000


@pytest.mark.anyio
async def test_list_scoring_jobs_history():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/scoring/jobs")
        assert res.status_code == 200
        jobs = res.json()
        assert len(jobs) >= 1
        assert jobs[0]["job_id"] == "test-job-01"
        assert jobs[0]["title"] == "历史作业1"
