import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate
from backend.app.db.seed import seed_candidates_if_empty
from sqlalchemy import select, func


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 插入测试用基因与候选靶点数据
    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(Gene.__table__.delete())

        test_gene = Gene(
            gene_id="LsaT2T01G023690",
            chrom="Chr01",
            start=83870025,
            end=83876080,
            strand="+",
            nlr_type="NLR-LRR",
            candidate_count=2,
        )
        session.add(test_gene)
        await session.flush()

        c1 = TargetCandidate(
            guide_id="Lsat_675191",
            gene_id="LsaT2T01G023690",
            chrom="Chr01",
            start=83868028,
            end=83868050,
            strand="+",
            seq30="TTTGTGGATTCCGGTAGAATCTGATGGAAT",
            seq20="TGGATTCCGGTAGAATCTGA",
            pam="TGG",
            region_type="promoter",
            is_centromere=False,
            is_exon=False,
            gc_pct=45.0,
            tm_c=58.0,
            offtarget_count_mis3=13,
            efficiency_score=24.54,
            deepspcas9_score=46.28,
            crispron_score=44.63,
        )

        c2 = TargetCandidate(
            guide_id="Lsat_675192",
            gene_id="LsaT2T01G023690",
            chrom="Chr01",
            start=83871000,
            end=83871022,
            strand="-",
            seq30="AAACCCCGGGGTTTTCCCCAAAATTTGGCC",
            seq20="CCCCGGGGTTTTCCCCAAAA",
            pam="CGG",
            region_type="exon",
            is_centromere=True,
            is_exon=True,
            gc_pct=60.0,
            tm_c=62.0,
            offtarget_count_mis3=2,
            efficiency_score=78.20,
            deepspcas9_score=80.15,
            crispron_score=75.30,
        )

        session.add_all([c1, c2])
        await session.commit()

    yield


@pytest.mark.anyio
async def test_get_genes_list():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/genes")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["gene_id"] == "LsaT2T01G023690"
    assert data[0]["chrom"] == "Chr01"


@pytest.mark.anyio
async def test_get_candidates_with_filtering():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. 默认查询所有
        res_all = await ac.get("/api/v1/candidates?gene_id=LsaT2T01G023690")
        assert res_all.status_code == 200
        all_data = res_all.json()
        assert all_data["total"] == 2
        assert len(all_data["items"]) == 2
        assert all_data["gene_summary"]["gene_id"] == "LsaT2T01G023690"

        # 2. 排除着丝粒
        res_no_centro = await ac.get(
            "/api/v1/candidates?gene_id=LsaT2T01G023690&exclude_centromere=true"
        )
        assert res_no_centro.status_code == 200
        no_centro_data = res_no_centro.json()
        assert no_centro_data["total"] == 1
        assert no_centro_data["items"][0]["guide_id"] == "Lsat_675191"

        # 3. 仅限外显子
        res_exon = await ac.get(
            "/api/v1/candidates?gene_id=LsaT2T01G023690&exon_only=true"
        )
        assert res_exon.status_code == 200
        exon_data = res_exon.json()
        assert exon_data["total"] == 1
        assert exon_data["items"][0]["guide_id"] == "Lsat_675192"

        # 4. 最低效率分过滤
        res_score = await ac.get(
            "/api/v1/candidates?gene_id=LsaT2T01G023690&min_score=50"
        )
        assert res_score.status_code == 200
        score_data = res_score.json()
        assert score_data["total"] == 1
        assert score_data["items"][0]["efficiency_score"] >= 50
