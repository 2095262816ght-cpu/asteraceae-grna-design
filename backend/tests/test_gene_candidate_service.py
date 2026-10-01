"""候选枚举 poly-T 硬过滤（教师反馈 #2）：含 TTTT 的 spacer 在枚举阶段剔除。"""
from pathlib import Path

from backend.app.services.gene_candidate_service import enumerate_gene_seq30


def _write_genome(tmp_path: Path, seq: str, name: str = "chrT") -> Path:
    fa = tmp_path / "genome.fa"
    with open(fa, "wb") as fh:
        fh.write(f">{name}\n".encode())
        for i in range(0, len(seq), 60):
            fh.write(seq[i : i + 60].encode() + b"\n")
    offset = len(f">{name}\n")
    (tmp_path / "genome.fa.fai").write_text(f"{name}\t{len(seq)}\t{offset}\t60\t61\n")
    return fa


def test_enumerate_filters_poly_t(tmp_path):
    # 两个 NGG 候选：一个 spacer 含 TTTT（应剔除），一个干净（应保留）
    good = "GGGGGGGGGGGGGGGGGGGG" + "TGG"  # 20nt + NGG
    bad = "AAAATTTTCCCCAAAATTTT" + "TGG"  # spacer 含 TTTT
    genome = "C" * 30 + good + "C" * 30 + bad + "C" * 30
    fa = _write_genome(tmp_path, genome)

    seq30s, note = enumerate_gene_seq30(fa, "chrT", 31, 200, "+", promoter=0, cap=100)
    spacers = [s[4:24] for s in seq30s]
    assert good[:20] in spacers
    assert bad[:20] not in spacers
    assert "TTTT" in note  # 过滤数量在口径说明中如实标注
