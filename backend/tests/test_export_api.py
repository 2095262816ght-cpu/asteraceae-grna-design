import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, GeneExpression, TargetCandidate, ExportBatch, ScoringJob


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await session.execute(ExportBatch.__table__.delete())
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
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


@pytest.mark.anyio
async def test_export_expression_evidence_and_uncomputed_columns():
    async with AsyncSessionLocal() as session:
        session.add(GeneExpression(
            gene_id="TEST_GENE_01", lsa_id="LSA999", tier=3, is_mappable=True,
            n_cluster=1, scaffold_evidence="HiC_scaffold_15",
        ))
        session.add(Gene(gene_id="TEST_GENE_02", chrom="chr2", start=100, end=900, strand="+", candidate_count=1))
        session.add(GeneExpression(
            gene_id="TEST_GENE_02", tier=4, is_mappable=False,
            unmappable_reason="测试理由：crosswalk 缺失",
        ))
        session.add(TargetCandidate(
            id=103, guide_id="guide_103", gene_id="TEST_GENE_02", chrom="chr2",
            start=200, end=230, strand="+",
            seq30="ATGGCATCGATTCGAGCTAAGGGTGCATGC",
            seq20="ATGGCATCGATTCGAGCTAA", pam="TGG",
            gc_pct=45.0, tm_c=66.0, efficiency_score=55.0,
        ))
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/api/v1/exports",
            json={"name": "证据判定", "format": "csv", "candidate_ids": [101, 102, 103]},
        )
        assert create_res.status_code == 201
        batch_id = create_res.json()["id"]
        dl_res = await ac.get(f"/api/v1/exports/{batch_id}/download")
        assert dl_res.status_code == 200

    import io
    import pandas as pd
    df = pd.read_csv(io.BytesIO(dl_res.content))

    assert "表达证据状态" in df.columns and "表达证据说明" in df.columns

    rows = {int(r["靶点唯一ID"]): r for _, r in df.iterrows()}
    # TEST_GENE_01：候选级未填 → 由基因级 tier=3 派生
    assert rows[101]["表达证据状态"] == "已映射（未挂载 scaffold）"
    assert "LSA999" in rows[101]["表达证据说明"]
    assert "HiC_scaffold_15" in rows[101]["表达证据说明"]
    # TEST_GENE_02：tier4 → 表达证据缺失 + 理由随导出带出
    assert rows[103]["表达证据状态"] == "表达证据缺失"
    assert rows[103]["表达证据说明"] == "测试理由：crosswalk 缺失"
    # 未计算如实渲染，不以 0 冒充；多组学 4 列不再静默留白
    for _, r in df.iterrows():
        assert r["潜在脱靶位点数(<=3)"] == "未计算"
        assert r["面板内位点数(49NLR面板)"] == "未计算"
        assert r["组织优先指数(叶)"] == "未计算"
        assert r["组织优先指数(根)"] == "未计算"
        assert r["功能性脱靶危害(叶)"] == "未计算"
        assert r["功能性脱靶危害(根)"] == "未计算"


@pytest.mark.anyio
async def test_export_xlsx_includes_methodology_sheet():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_res = await ac.post(
            "/api/v1/exports",
            json={"name": "方法说明", "format": "xlsx", "candidate_ids": [101, 102]},
        )
        assert create_res.status_code == 201
        batch_id = create_res.json()["id"]
        dl_res = await ac.get(f"/api/v1/exports/{batch_id}/download")
        assert dl_res.status_code == 200

    import io
    import pandas as pd
    xls = pd.ExcelFile(io.BytesIO(dl_res.content))
    assert "gRNA实验设计优选清单" in xls.sheet_names
    assert "指标方法说明" in xls.sheet_names

    text = "\n".join(
        xls.parse("指标方法说明").astype(str).agg(" ".join, axis=1).tolist()
    )
    # 老师三问的口径：综合分与两活性分的关系与权重、入模因素、脱靶计数来源
    assert "DeepSpCas9" in text and "CRISPRon" in text
    assert "标准化系数 β" in text
    assert "13.4%" in text
    assert "MIT" in text and "CFD" in text
    # 其余列与歧义口径同样备注
    assert "“未计算”≠ 0" in text
    assert "1-based 闭区间" in text
    assert "CCN" in text
    assert "组织优先指数" in text and "功能性脱靶危害" in text
    assert "表达证据状态" in text
    # 覆盖全部数据列名
    for col in pd.read_excel(io.BytesIO(dl_res.content), sheet_name="gRNA实验设计优选清单").columns:
        key = col.split("(")[0].split("（")[0]
        assert key in text, f"方法说明缺少对列 {col} 的备注"


@pytest.mark.anyio
async def test_export_reuses_computed_offtarget_without_download_rescan(monkeypatch):
    from backend.app.services import offtarget_service
    from backend.app.services.offtarget_service import OfftargetProfile

    fake_profile = OfftargetProfile(exact=1, mis1=2, mis2=3, mis3=7)
    scan_calls = []

    def fake_profiles(seq20s, genome_fasta=None):
        scan_calls.append(list(seq20s))
        return {s.upper(): fake_profile for s in seq20s}

    monkeypatch.setattr(offtarget_service, "compute_offtarget_profiles", fake_profiles)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 显式"按需脱靶计算"流程（导出前预计算：同口径 fill_missing_multiomics 回填持久化）
        compute_res = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": [101, 102]})
        assert compute_res.status_code == 200
        assert compute_res.json()["computed"] == 2
        scans_after_compute = len(scan_calls)

        create_res = await ac.post(
            "/api/v1/exports",
            json={"name": "按需脱靶", "format": "csv", "candidate_ids": [101, 102]},
        )
        assert create_res.status_code == 201
        batch_id = create_res.json()["id"]
        dl_res = await ac.get(f"/api/v1/exports/{batch_id}/download")
        assert dl_res.status_code == 200

    # 快下载：下载请求不再触发全基因组扫描（只读已回填的持久化值）
    assert len(scan_calls) == scans_after_compute

    import io
    import pandas as pd
    df = pd.read_csv(io.BytesIO(dl_res.content))
    assert (df["潜在脱靶位点数(<=3)"] == 7).all()
    # 优先指数：基因内百分位（101=1.0, 102=0.5），Penalty=0.295，无表达项
    rows = {int(r["靶点唯一ID"]): r for _, r in df.iterrows()}
    assert abs(rows[101]["组织优先指数(叶)"] - 0.42625) < 1e-6
    assert abs(rows[102]["组织优先指数(叶)"] - 0.17625) < 1e-6
    # 测试库无 NLR 面板 → 危害 0 且面板位点数 0（真实计算值）
    assert (df["功能性脱靶危害(叶)"] == 0.0).all()
    assert (df["面板内位点数(49NLR面板)"] == 0).all()

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        res = await session.execute(
            select(TargetCandidate.offtarget_count_mis3, TargetCandidate.priority_score_leaf, TargetCandidate.n_intra_panel_sites)
            .where(TargetCandidate.id == 101)
        )
        row = res.one()
        assert row[0] == 7
        assert abs(row[1] - 0.42625) < 1e-6
        assert row[2] == 0
