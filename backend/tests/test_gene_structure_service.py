"""基因结构解析（教师反馈 #3）：GFF 外显子/内含子/CDS/TSS + 区域判定。"""
from pathlib import Path

from backend.app.services.gene_structure_service import (
    PROMOTER_UPSTREAM,
    classify_gene_records,
    classify_position,
    gene_structure,
    load_gff_structure,
)

GFF_TEXT = """\
##gff-version 3
Chr1\ttest\tgene\t1000\t2000\t.\t+\t.\tID=GeneA
Chr1\ttest\tmRNA\t1000\t2000\t.\t+\t.\tID=GeneA.mRNA1;Parent=GeneA
Chr1\ttest\texon\t1000\t1200\t.\t+\t.\tID=GeneA.exon1;Parent=GeneA.mRNA1
Chr1\ttest\texon\t1500\t2000\t.\t+\t.\tID=GeneA.exon2;Parent=GeneA.mRNA1
Chr1\ttest\tCDS\t1050\t1200\t.\t+\t0\tID=GeneA.cds1;Parent=GeneA.mRNA1
Chr1\ttest\tgene\t5000\t6000\t.\t-\t.\tID=GeneB
Chr1\ttest\tmRNA\t5000\t6000\t.\t-\t.\tID=GeneB.mRNA1;Parent=GeneB
Chr1\ttest\texon\t5000\t5500\t.\t-\t.\tID=GeneB.exon1;Parent=GeneB.mRNA1
"""


def _write_gff(tmp_path: Path) -> Path:
    gff = tmp_path / "test.gff3"
    gff.write_text(GFF_TEXT, encoding="utf-8")
    return gff


def test_parse_structure_and_tss(tmp_path):
    genes = load_gff_structure(_write_gff(tmp_path))
    assert set(genes) == {"GeneA", "GeneB"}
    a = genes["GeneA"]
    assert (a["start"], a["end"], a["strand"]) == (1000, 2000, "+")
    assert a["tss"] == 1000  # + 链 TSS = 起点
    assert a["exons"] == [(1000, 1200), (1500, 2000)]
    assert a["cds"] == [(1050, 1200)]
    b = genes["GeneB"]
    assert b["tss"] == 6000  # - 链 TSS = 终点


def test_classify_positions(tmp_path):
    genes = load_gff_structure(_write_gff(tmp_path))
    assert classify_position(genes, "Chr1", 1100) == ("exon", "GeneA")
    assert classify_position(genes, "Chr1", 1300) == ("intron", "GeneA")
    assert classify_position(genes, "Chr1", 5200) == ("exon", "GeneB")
    # + 链启动子：TSS 上游 2kb 窗口
    assert classify_position(genes, "Chr1", 800) == ("promoter", "GeneA")
    # - 链启动子：TSS 下游（基因组方向）
    assert classify_position(genes, "Chr1", 6100) == ("promoter", "GeneB")
    assert classify_position(genes, "Chr1", 3000) == ("intergenic", None)
    # Chr01 命名兼容
    assert classify_position(genes, "Chr01", 1100) == ("exon", "GeneA")


RECORDS = {
    "Chr1": [
        {"gene_id": "GeneA", "start": 1000, "end": 2000, "strand": "+"},
        {"gene_id": "GeneB", "start": 5000, "end": 6000, "strand": "-"},
    ]
}


def test_classify_gene_records_body_and_windows():
    # 基因体按外显子近似标 exon（无外显子粒度数据源的既定口径）
    rtype, rec = classify_gene_records(RECORDS, "Chr1", 1500)
    assert (rtype, rec["gene_id"]) == ("exon", "GeneA")
    # + 链 TSS 上游窗口 / - 链 TSS 基因组下游窗口
    assert classify_gene_records(RECORDS, "Chr1", 800)[0] == "promoter"
    rtype, rec = classify_gene_records(RECORDS, "Chr1", 6100)
    assert (rtype, rec["gene_id"]) == ("promoter", "GeneB")
    assert classify_gene_records(RECORDS, "Chr1", 3000) == ("intergenic", None)
    # Chr01 命名兼容与 classify_position 一致
    assert classify_gene_records(RECORDS, "Chr01", 1500)[0] == "exon"


def test_classify_gene_records_window_boundaries():
    # PROMOTER_UPSTREAM 窗口为闭-开（+ 链）/ 开-闭（- 链），单点定义处唯一裁决
    assert classify_gene_records(RECORDS, "Chr1", 1000 - PROMOTER_UPSTREAM)[0] == "promoter"
    assert classify_gene_records(RECORDS, "Chr1", 999)[0] == "promoter"
    assert classify_gene_records(RECORDS, "Chr1", 6000 + PROMOTER_UPSTREAM)[0] == "promoter"
    assert classify_gene_records(RECORDS, "Chr1", 6000 + PROMOTER_UPSTREAM + 1)[0] == "intergenic"


def test_classify_gene_records_body_beats_promoter():
    overlap = {
        "Chr1": [
            {"gene_id": "WinGene", "start": 150, "end": 400, "strand": "+"},
            {"gene_id": "BodyGene", "start": 50, "end": 150, "strand": "-"},
        ]
    }
    # 140 同时落在 BodyGene 基因体与 WinGene 的 TSS 窗口内：基因体优先
    rtype, rec = classify_gene_records(overlap, "Chr1", 140)
    assert (rtype, rec["gene_id"]) == ("exon", "BodyGene")


def test_gene_structure_loci_fallback(tmp_path, monkeypatch):
    # LsaT2T 命名空间基因经 nlr_gene_loci.csv 重定位回退到 GFF 结构
    from backend.app.services import gene_structure_service as gs

    monkeypatch.setattr(gs, "_loci_cache", {
        "LsaDemo01G000001": {
            "gene_id": "LsaDemo01G000001",
            "orig_chrom": "Chr01", "orig_start": "5000", "orig_end": "6000",
            "remap_chrom": "Chr1", "remap_start": "1000", "remap_end": "2000",
            "offset": "4000", "gff_gene_id": "GeneA",
        }
    })
    monkeypatch.setattr(gs, "_domains_cache", [])
    rec = gene_structure(_write_gff(tmp_path), "LsaDemo01G000001")
    assert rec is not None
    assert rec["exons"] == [(1000, 1200), (1500, 2000)]
    assert rec["coordinate_note"] and "偏移" in rec["coordinate_note"]
    # 直接命中 GFF ID 时无坐标说明
    rec2 = gene_structure(_write_gff(tmp_path), "GeneA")
    assert rec2 is not None and rec2["coordinate_note"] is None
