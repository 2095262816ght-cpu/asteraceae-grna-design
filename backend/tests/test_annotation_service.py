"""C4/C5/C6 三态注释服务单测 + D1 参考包路由：precomputed / annotated / custom 三态与不硬猜纪律。"""
from pathlib import Path

import pytest
from sqlalchemy import delete

from backend.app.db.models import Base, Gene, GeneExpression, TargetCandidate
from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.services import gene_candidate_service as gc_service
from backend.app.services import reference_bundle_service as rb_service
from backend.app.services import sequence_annotation_service as sas
from backend.app.services.reference_bundle_service import ResolvedBundle

SEQ_PRE = "TTTGTGGATTCCGGTAGAATCTGATGGAAT"   # 命中预计算候选
SEQ_GENOME = "ATATGAAAATGTCAGGATGCCTGAAGGACA"  # 仅命中基因组（小合成基因组）
SEQ_CUSTOM = "GGGGGGGGGGGGGGGGGGGGGGGGGGGAAA"  # PAM=GGG? 见构造：须 NGG


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(TargetCandidate))
        await session.execute(delete(GeneExpression))
        await session.execute(delete(Gene))
        await session.commit()
    yield


def _fake_bundle(fasta: Path, **kw) -> ResolvedBundle:
    kw.setdefault("gene_source", "db")
    kw.setdefault("expression_layout", "db")
    return ResolvedBundle(
        id="mini",
        display_name="测试基因组",
        kind="imported",
        fasta=fasta,
        **kw,
    )


def _patch_bundle(monkeypatch, bundle: ResolvedBundle):
    async def _fake_load(db, bundle_id):
        return bundle

    monkeypatch.setattr(sas, "_load_bundle", _fake_load)


def _make_candidate(gene_id="LsT2T1G000010", seq30=SEQ_PRE, guide_id="T_G_001", eff=82.5):
    return TargetCandidate(
        guide_id=guide_id,
        gene_id=gene_id,
        chrom="Chr1",
        start=100,
        end=130,
        strand="+",
        seq30=seq30,
        seq20=seq30[4:24],
        pam=seq30[24:27],
        region_type="exon",
        is_centromere=False,
        is_exon=True,
        gc_pct=45.0,
        tm_c=50.0,
        offtarget_count_mis3=2,
        efficiency_score=eff,
        priority_score_leaf=0.61,
        hazard_leaf=0.12,
        expression_status="mapped",
        n_intra_panel_sites=1,
    )


def _make_gene(gene_id="LsT2T1G000010"):
    return Gene(
        gene_id=gene_id,
        chrom="Chr1",
        start=1,
        end=1000,
        strand="+",
        nlr_type="protein-coding",
        candidate_count=1,
    )


def _write_mini_genome(tmp_path, seq=SEQ_GENOME) -> Path:
    fasta = tmp_path / "mini.fa"
    fasta.write_text(f">Chr1\n{seq}\n")
    fai = tmp_path / "mini.fa.fai"
    fai.write_text(f"Chr1\t{len(seq)}\t6\t{len(seq)}\t{len(seq) + 1}\n")
    return fasta


@pytest.mark.anyio
async def test_state_precomputed_reuses_multiomics():
    async with AsyncSessionLocal() as session:
        session.add(_make_gene())
        session.add(_make_candidate())
        await session.commit()
    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(SEQ_PRE, session, bundle_id="lettuce", compute_offtarget=False)
    assert res["state"] == "precomputed"
    assert res["gene_id"] == "LsT2T1G000010"
    assert res["candidate"]["offtarget_count_mis3"] == 2
    assert res["candidate"]["priority_score_leaf"] == pytest.approx(0.61)
    assert res["candidate"]["expression_status"] == "mapped"


@pytest.mark.anyio
async def test_state_annotated_with_on_demand_profile(tmp_path, monkeypatch):
    # 构造只含目标位点的小基因组，回贴应命中并按需计算脱靶谱与优先指数
    fasta = _write_mini_genome(tmp_path)
    _patch_bundle(monkeypatch, _fake_bundle(fasta))

    async with AsyncSessionLocal() as session:
        session.add(_make_gene())
        session.add(_make_candidate())
        await session.commit()

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_GENOME, session, bundle_id="mini", efficiency_score=50.0, compute_offtarget=True
        )
    assert res["state"] == "annotated"
    assert res["hit"] is not None and res["hit"]["chrom"] == "Chr1"
    assert res["offtarget"] is not None
    # 命中自身不计脱靶：exact/mis 档按口径给出
    assert set(res["offtarget"]) == {"exact", "mis1", "mis2", "mis3"}
    # 优先指数按需计算且口径同 Tab 1（0-1 rank 百分位）
    assert res["priority_scores"] is not None
    assert all(0.0 <= v <= 1.0 for v in res["priority_scores"].values())
    assert "rank(pct=True) 同口径" in (res["priority_note"] or "")


@pytest.mark.anyio
async def test_state_custom_never_fabricates(tmp_path, monkeypatch):
    fasta = tmp_path / "mini.fa"
    fasta.write_text(">Chr1\nACGTACGTAC\n")
    (tmp_path / "mini.fa.fai").write_text("Chr1\t10\t6\t10\t11\n")
    _patch_bundle(monkeypatch, _fake_bundle(fasta))

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_CUSTOM, session, bundle_id="mini", efficiency_score=77.0, compute_offtarget=False
        )
    assert res["state"] == "custom"
    assert res["gene_id"] is None
    assert res["offtarget"] is None
    assert res["priority_scores"] is None
    assert "不硬算" in res["annotation_note"]


@pytest.mark.anyio
async def test_stage_expression_block_mapping_rule(tmp_path, monkeypatch):
    # evm.TU.X (GFF) → evm.model.X (表达矩阵) 规则映射与时相摘要构建
    import pandas as pd

    df = pd.DataFrame(
        {
            "Gene": ["evm.model.LG07.3296"],
            "S4-gen-1": [20.0], "S4-gen-2": [30.0],
            "S4-jiaoru-1": [100.0], "S4-jiaoru-2": [200.0],
            "S6-jiaoru-1": [300.0],
        }
    )
    df["Gene"] = df["Gene"].str.lower()
    df = df.set_index("Gene")
    monkeypatch.setattr(rb_service, "_load_expr_frame", lambda p: df)

    bundle = ResolvedBundle(
        id="tks",
        display_name="橡胶草 (TKS)",
        kind="preset",
        fasta=None,
        gene_source="gff",
        expression_path=tmp_path / "mem.xlsx",
        expression_layout="stage_tissue",
        expression_id_rule="evm_tu_to_model",
        tissue_columns={"根": "gen", "胶乳": "jiaoru", "叶": "ye"},
        notes="S4（方案6 产胶通路推荐转化窗口）",
    )

    blk = rb_service.stage_expression_block(bundle, "evm.TU.LG07.3296")
    assert blk is not None
    assert blk["matched_id"].lower() == "evm.model.lg07.3296"
    assert blk["stage_means"]["S4"]["gen"] == 25.0
    assert blk["stage_means"]["S4"]["jiaoru"] == 150.0
    assert blk["peak_stage_latex"] == "S6"
    assert blk["peak_stage_root"] == "S4"
    assert "S4" in blk["recommended_window"]
    # 无证据 → None（不编造）
    assert rb_service.stage_expression_block(bundle, "evm.TU.NOT_EXIST") is None


@pytest.mark.anyio
async def test_stage_tissue_priority_uses_peak_tpm(tmp_path, monkeypatch):
    # 方案3 TKS 口径（已确认：不加权、时相取峰值）：
    # 表达项(t) = sigmoid(log2(该组织 S1–S9 时相峰值 TPM+1)−2)，组织键随参考包；无证据组织不加分不倒扣
    import pandas as pd

    from backend.app.services.multiomics_service import expression_term
    from backend.app.services.offtarget_service import OfftargetProfile

    df = pd.DataFrame(
        {
            "Gene": ["evm.model.LG07.3296"],
            "S4-gen-1": [20.0], "S4-gen-2": [30.0],  # 根 S4 重复均值 25
            "S5-gen-1": [37.6],  # 根峰值（S5）
            "S4-jiaoru-1": [100.0], "S6-jiaoru-1": [300.0],  # 胶乳峰值（S6）300
            # 叶：无列 → 无证据 → 表达项 0
        }
    )
    df["Gene"] = df["Gene"].str.lower()
    df = df.set_index("Gene")
    monkeypatch.setattr(rb_service, "_load_expr_frame", lambda p: df)

    bundle = ResolvedBundle(
        id="tks",
        display_name="橡胶草 (TKS)",
        kind="preset",
        fasta=None,
        gene_source="gff",
        expression_path=tmp_path / "mem.xlsx",
        expression_layout="stage_tissue",
        expression_id_rule="evm_tu_to_model",
        tissue_columns={"根": "gen", "胶乳": "jiaoru", "叶": "ye"},
        notes="S4（方案6 产胶通路推荐转化窗口）",
    )

    peaks = rb_service.expression_stage_peaks(bundle, "evm.TU.LG07.3296")
    assert peaks == {"根": 37.6, "胶乳": 300.0}  # 无证据的叶不出现

    profile = OfftargetProfile(exact=1, mis1=0, mis2=0, mis3=1)  # 罚分 = (1 + 0.05)/10 = 0.105
    scores, note = sas._compose_priority(
        bundle, "evm.TU.LG07.3296", 0.91, profile, "按需计算（方案3 公式与 Tab 1 同源）"
    )
    assert list(scores.keys()) == ["根", "胶乳", "叶"]  # 组织键随参考包
    base = 0.50 * 0.91 - 0.25 * 0.105
    assert scores["根"] == pytest.approx(base + 0.25 * expression_term(37.6), abs=1e-6)
    assert scores["胶乳"] == pytest.approx(base + 0.25 * expression_term(300.0), abs=1e-6)
    assert scores["叶"] == pytest.approx(base, abs=1e-6)  # 无证据不加分不倒扣
    assert "时相峰值 TPM" in note

    # 未锚定基因 → 表达项 0（不编造）
    scores2, _ = sas._compose_priority(bundle, None, 0.91, profile, "x")
    assert scores2["根"] == pytest.approx(base, abs=1e-6)


@pytest.mark.anyio
async def test_priority_requires_distribution(tmp_path, monkeypatch):
    # 基因无预计算候选分布、现场批量打分也不可用 → 效率百分位无法定义 → 优先指数不计算（不硬猜）
    fasta = _write_mini_genome(tmp_path)
    _patch_bundle(monkeypatch, _fake_bundle(fasta))
    monkeypatch.setattr(gc_service, "score_seq30_batch", lambda *a, **k: None)  # 模拟推理不可用

    async with AsyncSessionLocal() as session:
        session.add(_make_gene(gene_id="LsT2T1G999999"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_GENOME, session, bundle_id="mini", efficiency_score=50.0, compute_offtarget=True
        )
    assert res["state"] == "annotated"
    assert res["gene_id"] == "LsT2T1G999999"
    assert res["priority_scores"] is None
    assert "无预计算候选分布" in (res["priority_note"] or "")
    assert "不硬猜" in (res["priority_note"] or "")


@pytest.mark.anyio
async def test_annotated_on_demand_distribution_percentile(tmp_path, monkeypatch):
    # 档②：库内无分布 → 现场枚举+批量打分构造同基因分布 → rank(pct=True) 真同口径百分位
    fasta = _write_mini_genome(tmp_path)
    _patch_bundle(monkeypatch, _fake_bundle(fasta))
    monkeypatch.setattr(
        gc_service,
        "gene_efficiency_distribution",
        lambda bundle, chrom, gene, own, eff, client=None: (
            [20.0, 30.0, 40.0, 55.0],
            "现场枚举该基因编码区+TSS 上游 2000bp 窗口双链全部 NGG 候选 5 条",
        ),
    )

    async with AsyncSessionLocal() as session:
        session.add(_make_gene(gene_id="LsT2T1G888888"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_GENOME, session, bundle_id="mini", efficiency_score=50.0, compute_offtarget=True
        )
    assert res["state"] == "annotated"
    assert res["priority_scores"] is not None
    # 50.0 在 [20,30,40,55] + 自身中的 rank(pct=True) = 0.8
    assert res["percentile"] == pytest.approx(0.8)
    assert "现场枚举" in (res["percentile_basis"] or "")
    assert "rank(pct=True) 同口径" in (res["priority_note"] or "")


@pytest.mark.anyio
async def test_custom_paste_set_percentile_and_offtarget(tmp_path, monkeypatch):
    # 档③：未锚定但给贴入集合 → 批内排名口径百分位 + 按需脱靶（对参考包基因组），表达项 0
    fasta = _write_mini_genome(tmp_path)
    _patch_bundle(monkeypatch, _fake_bundle(fasta))

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_CUSTOM,
            session,
            bundle_id="mini",
            efficiency_score=77.0,
            compute_offtarget=True,
            peer_efficiency_scores=[55.0, 60.0, 70.0],
        )
    assert res["state"] == "custom"
    assert res["offtarget"] is not None  # 未锚定也可算脱靶（相似位点计数）
    assert res["percentile"] == pytest.approx(1.0)  # 77 高于全部同批 → rank = 1.0
    assert "批内排名口径" in (res["percentile_basis"] or "")
    assert res["priority_scores"] is not None
    assert all(v <= 0.55 for v in res["priority_scores"].values())  # 表达项 0，上限 0.5*1.0
    assert len(res["missing_requirements"]) == 3


@pytest.mark.anyio
async def test_custom_single_without_peers_honest(tmp_path, monkeypatch):
    fasta = _write_mini_genome(tmp_path)
    _patch_bundle(monkeypatch, _fake_bundle(fasta))

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_CUSTOM, session, bundle_id="mini", efficiency_score=77.0, compute_offtarget=False
        )
    assert res["state"] == "custom"
    assert res["priority_scores"] is None
    assert res["percentile"] is None
    assert "单条无贴入集合" in (res["priority_note"] or "")


@pytest.mark.anyio
async def test_imported_bundle_tissue_tpm_priority(tmp_path, monkeypatch):
    # 导入参考包（GFF + 表达矩阵列映射）：基因定位走 GFF，优先指数按组织 TPM 口径
    fasta = _write_mini_genome(tmp_path)
    gff = tmp_path / "mini.gff3"
    # SEQ_GENOME 在 Chr1:1-30，基因覆盖 1-100
    gff.write_text("##gff-version 3\nChr1\ttest\tgene\t1\t100\t.\t+\t.\tID=GENE1\n")
    expr = tmp_path / "expr.csv"
    expr.write_text("GeneID,Leaf_tpm\nGENE1,25.0\n")

    bundle = _fake_bundle(
        fasta,
        gene_source="gff",
        gff=gff,
        expression_layout="tissue_tpm",
        expression_path=expr,
        tissue_columns={"叶": "Leaf_tpm"},
        expression_id_rule="same",
    )
    _patch_bundle(monkeypatch, bundle)

    async with AsyncSessionLocal() as session:
        session.add(_make_gene(gene_id="GENE1"))
        session.add(_make_candidate(gene_id="GENE1", seq30="A" * 27 + "TGG", guide_id="T_G_x1", eff=60.0))
        await session.commit()

    async with AsyncSessionLocal() as session:
        res = await sas.annotate_seq30(
            SEQ_GENOME, session, bundle_id="mini", efficiency_score=50.0, compute_offtarget=True
        )
    assert res["state"] == "annotated"
    assert res["gene_id"] == "GENE1"
    assert res["priority_scores"] is not None
    assert set(res["priority_scores"]) == {"叶"}
    assert 0.0 <= res["priority_scores"]["叶"] <= 1.0
    assert "组织 TPM 口径" in (res["priority_note"] or "")


@pytest.mark.anyio
async def test_ensure_fai_builds_index(tmp_path):
    fa = tmp_path / "g.fa"
    fa.write_text(">chrA desc\nACGTACGTAC\nGGGG\n>chrB\nTTTTTTTTTT\n")
    fai = rb_service.ensure_fai(fa)
    lines = fai.read_text().strip().split("\n")
    assert lines[0].startswith("chrA\t14\t")
    assert lines[1].startswith("chrB\t10\t")
