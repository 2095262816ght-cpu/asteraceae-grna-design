from pathlib import Path

import numpy as np
import pytest

from backend.app.db.models import GeneExpression
from backend.app.services import offtarget_service
from backend.app.services.multiomics_service import (
    _scan_panel_hits,
    hazard_scores,
    priority_scores,
)
from backend.app.services.offtarget_service import OfftargetProfile

SEQ20 = "ATGGCATCGATTCGAGCTAA"


def _write_genome(tmp_path: Path, seq: str, name: str = "chrT") -> Path:
    fa = tmp_path / "genome.fa"
    with open(fa, "wb") as fh:
        fh.write(f">{name}\n".encode())
        for i in range(0, len(seq), 60):
            fh.write(seq[i : i + 60].encode() + b"\n")
    offset = len(f">{name}\n")
    (tmp_path / "genome.fa.fai").write_text(f"{name}\t{len(seq)}\t{offset}\t60\t61\n")
    return fa


def _mutate(seq: str, positions) -> str:
    bases = {"A": "C", "C": "A", "G": "T", "T": "G"}
    s = list(seq)
    for p in positions:
        s[p] = bases[s[p]]
    return "".join(s)


def test_priority_scores_formula():
    profile = OfftargetProfile(exact=1, mis1=2, mis2=3, mis3=7)
    # Penalty = (1*1.0 + 2*0.5 + 3*0.2 + 7*0.05)/10 = 2.95/10 = 0.295
    # 无表达证据：0.5*1.0 - 0.25*0.295 = 0.42625
    scores = priority_scores(1.0, profile, None)
    assert abs(scores["leaf"] - 0.42625) < 1e-9
    assert scores["root"] == scores["leaf"]

    # 叶部 TPM=3 → E=log2(4)=2 → S=0.5 → +0.25*0.5
    expr = GeneExpression(gene_id="G", is_mappable=True, tpm_leaf=3.0)
    scores = priority_scores(1.0, profile, expr)
    assert abs(scores["leaf"] - 0.55125) < 1e-9
    assert abs(scores["root"] - 0.42625) < 1e-9  # 根部无 TPM → 表达项 0

    # 不可映射：表达项记 0（无证据即无加分）
    unmappable = GeneExpression(gene_id="G", is_mappable=False)
    assert priority_scores(1.0, profile, unmappable)["leaf"] == pytest.approx(0.42625)


def test_hazard_scores_formula():
    hits = [("PG1", 0), ("PG1", 3), ("PG2", 1)]
    panel_expr = {
        "PG1": {"root": 0.0, "stem": 0.0, "leaf": 3.0, "flower": 0.0, "seed": 0.0},
        "PG2": None,  # 不可映射 → 权重基线 0.1
    }
    out = hazard_scores(hits, panel_expr)
    # leaf: 10*(1+0.5*log2(4)) + 0.2*(1+0.5*log2(4)) + 3*0.1 = 20 + 0.4 + 0.3
    assert abs(out["leaf"] - 20.7) < 1e-9
    # root: 10*1 + 0.2*1 + 3*0.1
    assert abs(out["root"] - 10.5) < 1e-9
    assert out["n_intra"] == 3


def test_scan_panel_hits_locus_and_own_exclusion(tmp_path):
    site_m1 = _mutate(SEQ20, [3])  # 面板内 1 错配 → 计
    site_exact_own = SEQ20  # 自身 on-target（own 坐标）→ 不计
    site_outside = _mutate(SEQ20, [5, 9])  # 面板外 2 错配 → 不计
    genome = (
        "C" * 50
        + site_m1 + "TGG" + "C" * 8
        + site_exact_own + "TGG" + "C" * 8
        + site_outside + "TGG" + "C" * 50
    )
    fa = _write_genome(tmp_path, genome)
    fai_records = {r[0]: r for r in offtarget_service._load_fai(fa)}

    lo_m1 = 50
    lo_own = 50 + 20 + 3 + 8  # 81
    lo_out = lo_own + 20 + 3 + 8  # 112
    assert genome[lo_own : lo_own + 20] == SEQ20

    panel_loci = [("PG1", "chrT", 40, lo_own + 30)]  # 覆盖 m1 与 own，不含 outside
    hits = _scan_panel_hits(SEQ20, panel_loci, ("PG1", lo_own), fa, fai_records)
    assert hits == [("PG1", 1)]

    # 面板窗口不覆盖 outside 位点
    assert all(lo_out >= 40 + 30 for _ in [0])
