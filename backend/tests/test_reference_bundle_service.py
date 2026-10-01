"""D1/D2 参考包注册与解析单测：路径校验、列映射校验、预置包保护、清单。"""
from pathlib import Path

import pytest
from sqlalchemy import delete

from backend.app.db.models import Base, ReferenceBundle
from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.services import reference_bundle_service as rb_service


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ReferenceBundle))
        await session.commit()
    yield


def _write_files(tmp_path: Path, with_expr_cols=("Leaf",)) -> dict:
    fasta = tmp_path / "g.fa"
    fasta.write_text(">chrA\nACGTACGTACGTACGTACGTACGTACGTAC\n")
    gff = tmp_path / "g.gff3"
    gff.write_text("##gff-version 3\nchrA\ttest\tgene\t1\t30\t.\t+\t.\tID=G1\n")
    expr = tmp_path / "expr.csv"
    cols = ",".join(["GeneID", *with_expr_cols])
    expr.write_text(f"{cols}\nG1,25.0\n")
    return {"fasta": fasta, "gff": gff, "expr": expr}


@pytest.mark.anyio
async def test_register_bundle_persists_and_builds_fai(tmp_path):
    files = _write_files(tmp_path)
    async with AsyncSessionLocal() as session:
        summary = await rb_service.register_bundle(
            session,
            bundle_id="my_ref_v1",
            display_name="我的参考 v1",
            fasta_path=str(files["fasta"]),
            gff_path=str(files["gff"]),
            expression_path=str(files["expr"]),
            tissue_columns={"叶": "Leaf"},
        )
    assert summary["kind"] == "imported"
    assert summary["fasta_available"] and summary["gff_available"] and summary["expression_available"]
    assert summary["expression_layout"] == "tissue_tpm"
    assert Path(str(files["fasta"]) + ".fai").exists()  # .fai 自动构建

    async with AsyncSessionLocal() as session:
        bundle = await rb_service.resolve_bundle(session, "my_ref_v1")
    assert bundle.display_name == "我的参考 v1"
    assert bundle.gene_source == "gff"
    assert rb_service.expression_tpm(bundle, "G1") == {"叶": 25.0}
    assert rb_service.expression_tpm(bundle, "G_NOPE") is None


@pytest.mark.anyio
async def test_register_rejects_missing_mapped_column(tmp_path):
    files = _write_files(tmp_path, with_expr_cols=("Root",))
    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError, match="缺少映射列"):
            await rb_service.register_bundle(
                session,
                bundle_id="bad_map",
                display_name="坏映射",
                fasta_path=str(files["fasta"]),
                expression_path=str(files["expr"]),
                tissue_columns={"叶": "Leaf"},
            )


@pytest.mark.anyio
async def test_register_rejects_missing_fasta_and_preset_id(tmp_path):
    files = _write_files(tmp_path)
    async with AsyncSessionLocal() as session:
        with pytest.raises(ValueError, match="不存在"):
            await rb_service.register_bundle(
                session,
                bundle_id="no_fasta",
                display_name="x",
                fasta_path=str(tmp_path / "missing.fa"),
            )
        with pytest.raises(ValueError, match="预置包"):
            await rb_service.register_bundle(
                session,
                bundle_id="tks",
                display_name="覆盖预置",
                fasta_path=str(files["fasta"]),
            )


@pytest.mark.anyio
async def test_list_bundles_includes_presets_and_imported(tmp_path):
    files = _write_files(tmp_path)
    async with AsyncSessionLocal() as session:
        await rb_service.register_bundle(
            session,
            bundle_id="imported_x",
            display_name="导入包 x",
            fasta_path=str(files["fasta"]),
        )
        items = await rb_service.list_bundles(session)
    ids = [b["id"] for b in items]
    assert ids[:2] == ["lettuce", "tks"]
    assert "imported_x" in ids
