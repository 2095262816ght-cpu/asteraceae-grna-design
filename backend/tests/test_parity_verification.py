import pytest
import pandas as pd
from pathlib import Path
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.db.session import engine, AsyncSessionLocal
from backend.app.db.models import Base, Gene, TargetCandidate, GeneExpression
from backend.app.db.seed import seed_candidates_if_empty
from cs_pipeline.core.sequence_spec import validate_seq30, calc_gc, calc_tm


@pytest.fixture(autouse=True)
async def setup_parity_db():
    """初始化数据库并灌入全量 49 基因与候选靶点数据作为基准对照源。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 清空并确保重新完整灌入 49 个基准基因与候选数据
    async with AsyncSessionLocal() as session:
        await session.execute(TargetCandidate.__table__.delete())
        await session.execute(GeneExpression.__table__.delete())
        await session.execute(Gene.__table__.delete())
        await session.commit()

    await seed_candidates_if_empty()
    yield


@pytest.mark.anyio
async def test_gene_catalog_parity_with_demo_csv():
    """验收 1: 验证 49 个 NLR 基因元数据与基准数据 app_genes.csv 严格一致（并存方案下 API 为全基因组 + 49 NLR 超集）。"""
    csv_path = Path("cs_pipeline/demo/app_genes.csv")
    assert csv_path.exists(), "基准数据源 app_genes.csv 必须存在"
    df_genes_gt = pd.read_csv(csv_path)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/genes")

    assert res.status_code == 200
    api_genes = res.json()

    assert len(api_genes) >= len(df_genes_gt), (
        f"基因总数应不少于基准 {len(df_genes_gt)}（并存方案为全基因组 + 49 NLR 超集），实际为 {len(api_genes)}"
    )

    api_gene_map = {g["gene_id"]: g for g in api_genes}

    for _, row in df_genes_gt.iterrows():
        gid = str(row["gene_id"]).strip()
        assert gid in api_gene_map, f"基准基因 {gid} 必须存在于 API 响应中"
        ag = api_gene_map[gid]

        chrom = str(row.get("g_chrom", row.get("chrom"))).strip()
        start = int(row.get("g_start", row.get("start")))
        end = int(row.get("g_end", row.get("end")))
        strand = str(row.get("g_strand", row.get("strand"))).strip()

        assert ag["chrom"] == chrom
        assert ag["start"] == start
        assert ag["end"] == end
        assert ag["strand"] == strand
        assert ag["candidate_count"] > 0


@pytest.mark.anyio
async def test_candidate_scoring_and_ranking_parity():
    """验收 2: 验证代表性 NLR 基因靶点检索、终选效率分排序及所有生化指标与基准数据 100% 吻合。"""
    target_gene = "LsaT2T01G023690"
    csv_path = Path("cs_pipeline/demo/app_data.csv")
    assert csv_path.exists(), "基准数据源 app_data.csv 必须存在"

    df_cand_gt = pd.read_csv(csv_path)
    gene_gt = df_cand_gt[df_cand_gt["gene_id"] == target_gene].copy()
    assert not gene_gt.empty, f"基准数据应包含 {target_gene} 的候选靶点"

    # poly-T 硬过滤口径（教师反馈 #2）：含 TTTT 的候选在枚举/检索阶段被剔除，
    # 基线同样排除后逐字段比对；过滤数量单独断言（与 API gene_summary.poly_t_filtered_count 一致）
    n_poly_t_gt = int(gene_gt["seq20"].str.contains("TTTT").sum())
    gene_gt = gene_gt[~gene_gt["seq20"].str.contains("TTTT")].copy()

    # 按 efficiency_score 降序排布
    score_col = "efficiency_score_v21_nob879" if "efficiency_score_v21_nob879" in gene_gt.columns else "efficiency_score"
    gene_gt_sorted = gene_gt.sort_values(by=score_col, ascending=False).reset_index(drop=True)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(
            f"/api/v1/candidates?gene_id={target_gene}&page_size=50&sort_by=efficiency_score&sort_order=desc"
        )

    assert res.status_code == 200
    api_data = res.json()
    api_items = api_data["items"]
    assert len(api_items) > 0
    assert api_data["gene_summary"]["poly_t_filtered_count"] == n_poly_t_gt

    # 抽样前 10 个靶点进行逐字段高精度数值吻合度比对
    compare_n = min(10, len(api_items), len(gene_gt_sorted))
    for i in range(compare_n):
        gt_row = gene_gt_sorted.iloc[i]
        api_row = api_items[i]

        assert api_row["guide_id"] == str(gt_row["guide_id"]).strip()
        assert api_row["strand"] == str(gt_row["strand"]).strip()
        assert api_row["pam"] == str(gt_row["pam"]).strip()
        assert api_row["seq30"] == str(gt_row["seq30"]).strip()

        # 数值字段允许浮点舍入误差 (< 0.05)
        assert abs(api_row["gc_pct"] - float(gt_row["gc_pct"])) < 0.05
        assert abs(api_row["tm_c"] - float(gt_row["tm_c"])) < 0.05
        assert abs(api_row["efficiency_score"] - float(gt_row[score_col])) < 0.05

        if pd.notna(gt_row.get("deepspcas9_score")) and api_row["deepspcas9_score"] is not None:
            assert abs(api_row["deepspcas9_score"] - float(gt_row["deepspcas9_score"])) < 0.05

        if pd.notna(gt_row.get("crispron_score")) and api_row["crispron_score"] is not None:
            assert abs(api_row["crispron_score"] - float(gt_row["crispron_score"])) < 0.05


@pytest.mark.anyio
async def test_single_sequence_decomposition_parity(monkeypatch):
    """验收 3: 验证单序列打分 API 的解构区段 (5'Flank, Guide, PAM, 3'Flank) 与 GC%/Tm 计算和 core.sequence_spec 基准完全一致。"""
    # 模型不可用：效率分如实标缺失（本测试聚焦解构一致性，不依赖真实模型环境）
    monkeypatch.setattr("backend.app.services.scoring_service._HAS_INFERENCE_CLIENT", False)
    test_seq = "TTTGTGGATTCCGGTAGAATCTGATGGAAT"

    # 基准计算
    assert validate_seq30(test_seq) is None
    gt_flank5 = test_seq[0:4]
    gt_guide = test_seq[4:24]
    gt_pam = test_seq[24:27]
    gt_flank3 = test_seq[27:30]
    gt_gc = round(calc_gc(gt_guide) * 100, 1)
    gt_tm = round(calc_tm(gt_guide), 1)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            "/api/v1/scoring/single",
            json={"seq30": test_seq, "title": "一致性比对"},
        )

    assert res.status_code == 200
    data = res.json()

    assert data["flank_5p"] == gt_flank5
    assert data["guide_seq"] == gt_guide
    assert data["pam"] == gt_pam
    assert data["flank_3p"] == gt_flank3
    assert abs(data["gc_pct"] - gt_gc) < 0.01
    assert abs(data["tm_c"] - gt_tm) < 0.01
    assert data["efficiency_score"] is None
    assert "未计算" in (data["warning_message"] or "")
