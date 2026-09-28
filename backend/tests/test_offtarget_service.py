from pathlib import Path

import pytest

from backend.app.services.offtarget_service import (
    _revcomp,
    compute_offtarget_counts,
    count_offtargets_for_seq20,
)

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


def _brute_force(seq20: str, genome: str) -> int:
    """行口径（同 Cas-OFFinder + scripts/09 聚合）：NGG PAM 合格的链特异行，错配 1..3。"""
    rc = _revcomp(seq20)
    n = 0
    for w in range(len(genome) - 19):
        window = genome[w : w + 20]
        if w + 22 < len(genome) and genome[w + 21] == "G" and genome[w + 22] == "G":
            h = sum(a != b for a, b in zip(window, seq20))
            if 1 <= h <= 3:
                n += 1
        if w >= 3 and genome[w - 3] == "C" and genome[w - 2] == "C":
            h = sum(a != b for a, b in zip(window, rc))
            if 1 <= h <= 3:
                n += 1
    return n


def test_count_offtargets_matches_brute_force(tmp_path):
    fwd_sites = [
        SEQ20,  # 完全匹配（正链行 0 错配，不计）
        _mutate(SEQ20, [3]),  # 1 错配 → 计
        _mutate(SEQ20, [2, 7, 15]),  # 3 错配 → 计
        _mutate(SEQ20, [1, 5, 9, 13]),  # 4 错配 → 不计
        _mutate(SEQ20, [0, 8]),  # 2 错配但无 NGG PAM → 不计
    ]
    rc_sites = [
        _revcomp(SEQ20),  # 负链完全匹配 → 不计
        _mutate(_revcomp(SEQ20), [4, 11]),  # 负链 2 错配（前导 CC 来自 C 填充）→ 计
    ]

    parts = ["C" * 50]
    for site in fwd_sites:
        parts += [site, "TGG", "C" * 25]  # TGG 提供 NGG PAM
    # 无 PAM 的 2 错配位点（PAM 位置给 CCC，破坏 GG）
    parts[parts.index(_mutate(SEQ20, [0, 8])) + 1] = "CCC"
    for site in rc_sites:
        parts += [site, "C" * 25]  # 前导 C 填充提供 CCN
    parts += ["C" * 50]
    genome = "".join(parts)

    fa = _write_genome(tmp_path, genome)

    expected = _brute_force(SEQ20, genome)
    # 设计命中：正链 1 错配 + 正链 3 错配 + 负链 2 错配 = 3 行
    assert expected == 3

    got = count_offtargets_for_seq20(SEQ20, fa)
    assert got == expected


def test_exact_matches_excluded(tmp_path):
    # 完全匹配行不计：正链 exact（带 NGG）与负链 exact（前导 CC）都不产生计数
    genome = "C" * 40 + SEQ20 + "TGG" + "C" * 40 + _revcomp(SEQ20) + "C" * 40
    fa = _write_genome(tmp_path, genome)
    assert count_offtargets_for_seq20(SEQ20, fa) == 0


def test_compute_offtarget_counts_dedup_and_missing_genome(tmp_path):
    genome = "C" * 40 + _mutate(SEQ20, [0, 8]) + "TGG" + "C" * 40
    fa = _write_genome(tmp_path, genome)
    counts = compute_offtarget_counts([SEQ20, SEQ20.lower()], genome_fasta=fa)
    assert counts == {SEQ20: _brute_force(SEQ20, genome)}
    assert counts[SEQ20] == 1

    with pytest.raises(FileNotFoundError):
        compute_offtarget_counts([SEQ20], genome_fasta=tmp_path / "no_such.fa")
