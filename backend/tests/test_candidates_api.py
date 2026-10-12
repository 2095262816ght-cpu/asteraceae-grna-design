import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate, GeneExpression
from backend.app.db.seed import seed_candidates_if_empty
from sqlalchemy import select, func


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 插入测试用基因与候选靶点数据
    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
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

        expr = GeneExpression(
            gene_id="LsaT2T01G023690",
            lsa_id="LSA25643",
            tier=1,
            lsa_vote_frac=0.819,
            is_mappable=True,
            tpm_root=3.385,
            tpm_stem=1.428,
            tpm_leaf=0.951,
            tpm_flower=1.09,
            tpm_seed=1.72,
            top_tissue="根",
            top_tpm=3.385,
            tau=0.62,
        )
        session.add(expr)

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
            priority_score_leaf=0.85,
            priority_score_root=0.30,
            hazard_leaf=0.05,
            expression_status="mapped_cluster",
        )

        c2 = TargetCandidate(
            guide_id="Lsat_675192",
            gene_id="LsaT2T01G023690",
            chrom="Chr01",
            start=83871000,
            end=83871022,
            strand="-",
            seq30="AAACCCCCGGGGTTTACCCCAAAACGGGGC",
            seq20="CCCCGGGGTTTACCCCAAAA",
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
            priority_score_leaf=0.45,
            priority_score_root=0.90,
            hazard_leaf=0.00,
            expression_status="mapped_cluster",
        )

        # poly-T 硬过滤样本：seq20 含 TTTT（U6 转录终止信号），应不出现在候选列表
        c3 = TargetCandidate(
            guide_id="Lsat_675193",
            gene_id="LsaT2T01G023690",
            chrom="Chr01",
            start=83872000,
            end=83872022,
            strand="+",
            seq30="AAACCCCCGGGGTTTTCCCCAAAACGGGGC",
            seq20="CCCCGGGGTTTTCCCCAAAA",
            pam="CGG",
            region_type="exon",
            is_centromere=False,
            is_exon=True,
            gc_pct=60.0,
            tm_c=62.0,
            offtarget_count_mis3=1,
            efficiency_score=90.00,
            deepspcas9_score=85.0,
            crispron_score=80.0,
            expression_status="mapped_cluster",
        )

        session.add_all([c1, c2, c3])
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
        # 1. 默认查询所有（含 TTTT 的 c3 已被 poly-T 硬过滤）
        res_all = await ac.get("/api/v1/candidates?gene_id=LsaT2T01G023690")
        assert res_all.status_code == 200
        all_data = res_all.json()
        assert all_data["total"] == 2
        assert len(all_data["items"]) == 2
        assert all_data["gene_summary"]["gene_id"] == "LsaT2T01G023690"
        assert all_data["gene_summary"]["poly_t_filtered_count"] == 1
        assert all(i["guide_id"] != "Lsat_675193" for i in all_data["items"])
        # 表达适配度字段（MFE/5'G）
        assert all(i["expression_fitness_note"] for i in all_data["items"])

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


@pytest.mark.anyio
async def test_gene_expression_api():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/genes/LsaT2T01G023690/expression")

    assert res.status_code == 200
    data = res.json()
    assert data["gene_id"] == "LsaT2T01G023690"
    assert data["is_mappable"] is True
    assert data["lsa_id"] == "LSA25643"
    assert data["top_tissue"] == "根"
    assert abs(data["top_tpm"] - 3.385) < 0.01
    assert data["tpm_dict"]["Leaf"] == 0.951
    assert data["tau"] == 0.62


@pytest.mark.anyio
async def test_target_tissue_candidates_sorting():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 当 target_tissue=Leaf，按 priority_score 降序排序，c1 (priority 0.85) 应排在 c2 (0.45) 前
        res_leaf = await ac.get(
            "/api/v1/candidates?gene_id=LsaT2T01G023690&target_tissue=Leaf&sort_by=priority_score&sort_order=desc"
        )
        assert res_leaf.status_code == 200
        leaf_items = res_leaf.json()["items"]
        assert leaf_items[0]["guide_id"] == "Lsat_675191"
        assert leaf_items[0]["priority_score"] == 0.85
        assert leaf_items[0]["hazard_score"] == 0.05
        assert leaf_items[0]["expression_status_display"] == "已映射（串联簇）"

        # 当 target_tissue=Root，按 priority_score 降序排序，c2 (root priority 0.90) 应排在 c1 (0.30) 前
        res_root = await ac.get(
            "/api/v1/candidates?gene_id=LsaT2T01G023690&target_tissue=Root&sort_by=priority_score&sort_order=desc"
        )
        assert res_root.status_code == 200
        root_items = res_root.json()["items"]
        assert root_items[0]["guide_id"] == "Lsat_675192"
        assert root_items[0]["priority_score"] == 0.90
