"""脱靶位点详情端点（教师反馈 #1）：monkeypatch 扫描核心，验证响应口径与在靶排除。"""
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.services import offtarget_service
from backend.app.services.offtarget_service import OfftargetProfile

SEQ20 = "ATGGCATCGATTCGAGCTAA"

_CANNED_SITES = [
    {
        "chrom": "Chr1", "start": 100, "end": 119, "strand": "+",
        "protospacer20": SEQ20, "pam": "TGG",
        "mismatch_count": 0, "mismatch_positions": [],
        "cfd_score": 1.0, "mit_hit_score": 100.0,
    },
    {
        "chrom": "Chr1", "start": 500, "end": 519, "strand": "-",
        "protospacer20": "C" + SEQ20[1:], "pam": "AGG",
        "mismatch_count": 1, "mismatch_positions": [1],
        "cfd_score": 0.5, "mit_hit_score": 60.5,
    },
]


@pytest.fixture
def fake_scan(monkeypatch, tmp_path):
    def _scan(seq20, fasta, max_sites=200):
        return OfftargetProfile(exact=1, mis1=1, mis2=1, mis3=1), [dict(s) for s in _CANNED_SITES]

    monkeypatch.setattr(offtarget_service, "scan_seq20", _scan)
    # lettuce 预置包在测试环境无真实基因组：伪造 bundle
    from backend.app.api.v1.endpoints import offtarget as offtarget_ep

    fake_fa = tmp_path / "genome.fa"
    fake_fa.write_text(">Chr1\nACGT\n")

    class _FakeBundle:
        id = "lettuce"
        display_name = "莴苣 (LsT2T)"
        fasta = fake_fa
        gff = None

    async def _resolve(db, bundle_id):
        return _FakeBundle()

    monkeypatch.setattr(offtarget_ep, "resolve_bundle", _resolve)
    return _scan


@pytest.mark.anyio
async def test_offtarget_sites_endpoint(fake_scan):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/offtarget/sites?seq20={SEQ20}&ontarget_start=100&ontarget_end=119"
        )
    assert res.status_code == 200
    data = res.json()
    assert data["seq20"] == SEQ20
    assert data["profile"] == {"exact": 1, "mis1": 1, "mis2": 1, "mis3": 1}
    assert len(data["sites"]) == 2
    # 在靶位点被标记并排除出风险汇总
    ontarget = [s for s in data["sites"] if s["is_ontarget"]]
    assert len(ontarget) == 1
    assert ontarget[0]["start"] == 100
    assert ontarget[0]["risk_level"] == "在靶"
    other = [s for s in data["sites"] if not s["is_ontarget"]][0]
    assert other["mismatch_count"] == 1
    assert other["risk_level"] == "高危"
    assert other["mismatch_positions"] == [1]
    # CFD/MIT 位点评分透传 + guide 级特异性（排除在靶 1 个）
    assert other["cfd_score"] == 0.5
    assert data["specificity"]["n_offtarget_sites_scored"] == 1
    assert data["specificity"]["on_target_excluded"] is True
    assert "Cas-OFFinder" in data["method_note"]


@pytest.mark.anyio
async def test_offtarget_sites_invalid_seq():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/offtarget/sites?seq20=ACGT")
    assert res.status_code == 422  # 长度校验


# ============ POST /offtarget/compute：按需计算脱靶并回填（点击"未计算"/导出前预计算） ============

@pytest.fixture
async def compute_db():
    from backend.app.db.session import engine, AsyncSessionLocal
    from backend.app.db.models import Base, Gene, GeneExpression, TargetCandidate

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
        await session.execute(Gene.__table__.delete())
        session.add(
            Gene(gene_id="TEST_GENE_01", chrom="chr1", start=1000, end=5000, strand="+", candidate_count=1)
        )
        session.add(
            TargetCandidate(
                id=301,
                guide_id="guide_301",
                gene_id="TEST_GENE_01",
                chrom="chr1",
                start=1200,
                end=1230,
                strand="+",
                seq30="TTTGTGGATTCCGGTAGAATCTGATGGAAT",
                seq20=SEQ20,
                pam="TGG",
                gc_pct=45.0,
                tm_c=69.0,
                efficiency_score=85.2,
            )
        )
        await session.commit()
    yield


@pytest.fixture
def fake_profiles(monkeypatch):
    def _compute(seq20s, genome_fasta=None):
        return {s.upper(): OfftargetProfile(exact=1, mis1=2, mis2=3, mis3=4) for s in seq20s}

    monkeypatch.setattr(offtarget_service, "compute_offtarget_profiles", _compute)
    return _compute


@pytest.mark.anyio
async def test_compute_offtarget_persists_and_is_idempotent(compute_db, fake_profiles):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": [301]})
        assert res.status_code == 200
        data = res.json()
        assert data["computed"] == 1
        assert data["items"][0] == {"id": 301, "offtarget_count_mis3": 4, "n_intra_panel_sites": 0}

        # 幂等：已回填的候选不再扫描，返回同值
        res2 = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": [301]})
        assert res2.status_code == 200
        assert res2.json()["computed"] == 0
        assert res2.json()["items"][0]["offtarget_count_mis3"] == 4


@pytest.mark.anyio
async def test_compute_offtarget_error_paths(compute_db, monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 空列表 → 422
        res = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": []})
        assert res.status_code == 422

        # 未知候选 → 404
        res = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": [99999]})
        assert res.status_code == 404

        # 参考基因组不可用 → 503（如实报错，不以 0 冒充）
        def _raise(seq20s, genome_fasta=None):
            raise FileNotFoundError("T2T 基因组 FASTA 不存在")

        monkeypatch.setattr(offtarget_service, "compute_offtarget_profiles", _raise)
        res = await ac.post("/api/v1/offtarget/compute", json={"candidate_ids": [301]})
        assert res.status_code == 503
