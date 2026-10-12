from pathlib import Path

import pytest

from backend.app.services.offtarget_service import (
    _revcomp,
    compute_offtarget_counts,
    count_offtargets_for_seq20,
    profile_seq20,
    scan_seq20,
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


def test_profile_bands(tmp_path):
    # 分档口径（同 scripts/09）：exact=0错配行数；mis1/2/3 为 1..k 错配累计行数
    genome = (
        "C" * 50
        + SEQ20 + "TGG" + "C" * 25
        + _mutate(SEQ20, [3]) + "TGG" + "C" * 25
        + _mutate(SEQ20, [2, 7]) + "TGG" + "C" * 25
        + _mutate(SEQ20, [2, 7, 15]) + "TGG" + "C" * 50
    )
    fa = _write_genome(tmp_path, genome)
    p = profile_seq20(SEQ20, fa)
    assert (p.exact, p.mis1, p.mis2, p.mis3) == (1, 1, 2, 3)


def test_genome_end_boundary_no_index_error(tmp_path):
    # 回归：候选窗口落在基因组最末端时正链 PAM 越界，不得抛 IndexError；
    # 末端窗口的负链行（前导 CC）仍照常计数
    tail = _mutate(_revcomp(SEQ20), [4])  # 负链 1 错配，窗口恰好止于基因组末端
    genome = "C" * 50 + tail
    fa = _write_genome(tmp_path, genome)
    expected = _brute_force(SEQ20, genome)
    assert expected == 1
    assert count_offtargets_for_seq20(SEQ20, fa) == expected


def test_compute_offtarget_counts_dedup_and_missing_genome(tmp_path):
    genome = "C" * 40 + _mutate(SEQ20, [0, 8]) + "TGG" + "C" * 40
    fa = _write_genome(tmp_path, genome)
    counts = compute_offtarget_counts([SEQ20, SEQ20.lower()], genome_fasta=fa)
    assert counts == {SEQ20: _brute_force(SEQ20, genome)}
    assert counts[SEQ20] == 1

    with pytest.raises(FileNotFoundError):
        compute_offtarget_counts([SEQ20], genome_fasta=tmp_path / "no_such.fa")


def _check_site_record(site: dict, genome: str):
    """位点记录内部自洽：坐标窗口、方向、错配位置、评分与序列一致。"""
    window = genome[site["start"] - 1 : site["end"]]
    if site["strand"] == "+":
        assert site["protospacer20"] == window
    else:
        assert site["protospacer20"] == _revcomp(window)
    assert site["pam"][1:] == "GG"
    # 错配位置（gRNA 方向 1-based）与实际比对一致
    for p in site["mismatch_positions"]:
        assert site["protospacer20"][p - 1] != SEQ20[p - 1]
    assert len(site["mismatch_positions"]) == site["mismatch_count"]
    # CFD 可为 0（部分错配类型实证切割频率为 0）
    assert 0.0 <= site["cfd_score"] <= 1.0
    assert 0.0 < site["mit_hit_score"] <= 100.0


def test_scan_seq20_site_details(tmp_path):
    # 正链 exact + 1/2/3 错配四行（同 test_profile_bands 基因组）
    genome = (
        "C" * 50
        + SEQ20 + "TGG" + "C" * 25
        + _mutate(SEQ20, [3]) + "TGG" + "C" * 25
        + _mutate(SEQ20, [2, 7]) + "TGG" + "C" * 25
        + _mutate(SEQ20, [2, 7, 15]) + "TGG" + "C" * 50
    )
    fa = _write_genome(tmp_path, genome)
    profile, sites = scan_seq20(SEQ20, fa)
    assert (profile.exact, profile.mis1, profile.mis2, profile.mis3) == (1, 1, 2, 3)
    assert len(sites) == 4

    by_mm = {s["mismatch_count"]: s for s in sites}
    for s in sites:
        _check_site_record(s, genome)

    # 完全匹配位点：CFD=1.0，MIT=100
    assert by_mm[0]["cfd_score"] == 1.0
    assert by_mm[0]["mit_hit_score"] == 100.0
    # 1 错配（模板 idx 3 → gRNA 方向 4）
    assert by_mm[1]["mismatch_positions"] == [4]
    # 3 错配（模板 idx 2,7,15 → gRNA 方向 3,8,16）
    assert by_mm[3]["mismatch_positions"] == [3, 8, 16]
    # 坐标与基因组一致（1-based 闭区间）
    s1 = by_mm[1]
    assert genome[s1["start"] - 1 : s1["end"]] == _mutate(SEQ20, [3])


def test_scan_seq20_negative_strand_positions(tmp_path):
    # 负链位点：错配位置须换算到 gRNA 方向（20 - 窗口下标）
    rc_site = _mutate(_revcomp(SEQ20), [4, 11])  # 窗口下标 4/11 → gRNA 方向 16/9
    genome = "C" * 50 + rc_site + "C" * 50
    fa = _write_genome(tmp_path, genome)
    profile, sites = scan_seq20(SEQ20, fa)
    assert profile.mis3 == 1
    assert len(sites) == 1
    s = sites[0]
    _check_site_record(s, genome)
    assert s["strand"] == "-"
    assert set(s["mismatch_positions"]) == {9, 16}


def test_scan_sites_truncated_but_counts_exact(tmp_path):
    genome = "C" * 40
    for _ in range(5):
        genome += _mutate(SEQ20, [3]) + "TGG" + "C" * 25
    fa = _write_genome(tmp_path, genome)
    profile, sites = scan_seq20(SEQ20, fa, max_sites=2)
    assert profile.mis3 == 5  # 计数全量精确
    assert len(sites) == 2  # 明细截断


def test_scan_cache_shared_between_count_and_site_paths(tmp_path, monkeypatch):
    # 计数与位点明细共享同一次扫描：按需计算脱靶后打开明细抽屉不重扫全基因组（反之亦然）
    import backend.app.services.offtarget_service as osvc

    genome = "C" * 50 + SEQ20 + "TGG" + "C" * 25 + _mutate(SEQ20, [3]) + "TGG" + "C" * 50
    fa = _write_genome(tmp_path, genome)

    calls = []
    real_scan = osvc._scan_seq20

    def counting_scan(*args, **kwargs):
        calls.append(args)
        return real_scan(*args, **kwargs)

    monkeypatch.setattr(osvc, "_scan_seq20", counting_scan)

    p = profile_seq20(SEQ20, fa)  # 首次：扫描 1 次并写缓存
    assert (p.exact, p.mis3) == (1, 1)
    assert len(calls) == 1

    profile, sites = scan_seq20(SEQ20, fa)  # 位点明细：缓存命中，不再扫描
    assert profile == p
    assert len(sites) == 2
    assert len(calls) == 1

    # 返回缓存副本：调用方就地补注释不污染缓存
    sites[0]["region_label"] = "污染测试"
    _, sites2 = scan_seq20(SEQ20, fa)
    assert "region_label" not in sites2[0]

    # 计数入口同样命中缓存
    assert count_offtargets_for_seq20(SEQ20, fa) == p.mis3
    assert len(calls) == 1
