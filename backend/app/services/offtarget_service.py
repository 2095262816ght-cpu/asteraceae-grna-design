"""全基因组潜在脱靶位点按需计数（导出批次时计算并回填缓存）。

口径与 demo Cas-OFFinder 聚合一致（cs_pipeline/scripts/09_aggregate_offtarget.py +
data/lettuce/casoffinder_input.txt 模式行 NNNNNNNNNNNNNNNNNNNNNNGG）：
- 20-mer 错配数 1..3 的链特异行（不含完全匹配行本身）
- PAM 要求 NGG：正链行要求窗口后紧随 NGG（正链读作 NGG），负链行等价于正链读作 CCN
- 行计数口径：同一基因组位点若双链均合格则计两行（与 Cas-OFFinder 逐行聚合一致，罕见）

实现：鸽笼原理种子筛——≤3 错配 ⇒ 4 个不重叠 5-mer 块必有一块精配。
逐染色体按 .fai 分块读取，块内 5-mer 三进制编码（A/C/G/T/N 五值）做块过滤，
候选窗口先做 PAM 合格性过滤再向量化 Hamming 验证。近似约定：含 N 的 5-mer 与
guide 块码必然不匹配，N 密集窗口可能被漏计（对计数影响可忽略，如实标注于此）。
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

LUT = np.full(256, 4, dtype=np.uint8)
for _i, _b in enumerate(b"ACGT"):
    LUT[_b] = _i
    LUT[_b + 32] = _i  # 小写软掩蔽

COMP = np.full(256, 4, dtype=np.uint8)
for _a, _b in zip(b"ACGT", b"TGCA"):
    COMP[_a] = _b
    COMP[_a + 32] = _b + 32
COMP[ord("N")] = ord("N")
COMP[ord("n")] = ord("n")

BLOCK = 5
N_BLOCKS = 4
WINDOW = 20
CHUNK_BASES = 8_000_000
VERIFY_BATCH = 500_000
PAD_BEFORE = 3  # 负链行 PAM(=正链 CCN) 在窗口前 3bp
PAD_AFTER = 23  # 窗口 20bp + 正链 PAM NGG 3bp
CODE_C = 1
CODE_G = 2

BASES_ASCII = np.array([65, 67, 71, 84, 78], dtype=np.uint8)  # ACGTN
COMP_CODE = np.array([3, 2, 1, 0, 4], dtype=np.uint8)  # A<->T, C<->G, N->N
MAX_SITES = 200  # 位点明细返回上限（计数仍全量精确）

# 进程内计数缓存：(基因组路径, seq20) -> 分档计数
_COUNT_CACHE: Dict[Tuple[str, str], "OfftargetProfile"] = {}
# 进程内位点明细缓存：(基因组路径, seq20, max_sites) -> (分档计数, 位点列表)
_SITE_CACHE: Dict[Tuple[str, str, int], Tuple["OfftargetProfile", List[dict]]] = {}


def _cache_key(fasta: Path) -> str:
    return str(Path(fasta))


@dataclass(frozen=True)
class OfftargetProfile:
    """脱靶分档计数（同 cs_pipeline/scripts/09 聚合口径）：

    exact = 完全匹配行数；mis1/mis2/mis3 = 1..k 错配的**累计**行数（mis3 即原"潜在脱靶位点数(<=3)"）。
    """
    exact: int
    mis1: int
    mis2: int
    mis3: int


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_genome_fasta() -> Path:
    p = Path(settings.T2T_GENOME_FASTA)
    if not p.is_absolute():
        p = _repo_root() / p
    return p


def _load_fai(fasta: Path) -> List[Tuple[str, int, int, int, int]]:
    fai = fasta.with_suffix(fasta.suffix + ".fai")
    if not fai.exists():
        raise FileNotFoundError(f"缺少 FASTA 索引: {fai}")
    records = []
    with open(fai, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            records.append((parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])))
    return records


def _fetch(fasta: Path, rec: Tuple[str, int, int, int, int], start: int, end: int) -> bytes:
    """读取 [start, end) 区间的碱基字节（去除换行）。"""
    _, length, offset, linebases, linewidth = rec
    end = min(end, length)
    if start >= end:
        return b""
    line_skip = linewidth - linebases
    file_start = offset + start + (start // linebases) * line_skip
    n_lines = (end - start + (start % linebases)) // linebases + 1
    n_bytes = (end - start) + n_lines * line_skip + linewidth
    with open(fasta, "rb") as fh:
        fh.seek(file_start)
        raw = fh.read(n_bytes)
    arr = np.frombuffer(raw, dtype=np.uint8)
    arr = arr[(arr != 10) & (arr != 13)]
    return arr[: end - start].tobytes()


def _pack_codes(t: np.ndarray) -> np.ndarray:
    """5-mer 编码：C[w] = code(t[w:w+5])，3bit×5，含 N 码值 4。"""
    n = t.size - (BLOCK - 1)
    c = np.zeros(n, dtype=np.uint16)
    for k in range(BLOCK):
        c |= t[k : k + n].astype(np.uint16) << (3 * (BLOCK - 1 - k))
    return c


def _pattern_block_codes(pattern: np.ndarray) -> List[Tuple[int, int]]:
    """返回 [(块偏移, 块码)]，块码与 _pack_codes 同一 3bit×5 编码。"""
    out = []
    for o in range(0, WINDOW, BLOCK):
        bc = 0
        for k in range(BLOCK):
            bc |= int(pattern[o + k]) << (3 * (BLOCK - 1 - k))
        out.append((o, bc))
    return out


def _revcomp(seq20: str) -> str:
    return seq20.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


def count_offtargets_for_seq20(seq20: str, fasta: Path) -> int:
    """兼容包装：返回 mis3（1..3 错配累计行数）。"""
    return profile_seq20(seq20, fasta).mis3


def profile_seq20(seq20: str, fasta: Path) -> OfftargetProfile:
    """全基因组脱靶分档：20-mer 错配 0..3 且 PAM 为 NGG 的链特异行（分档累计口径）。

    经 scan_seq20 的共享缓存取数（顺带收集位点明细），使"按需计算脱靶"之后
    打开位点明细抽屉零重复扫描（反之亦然）。
    """
    seq20 = seq20.upper()
    key = (_cache_key(fasta), seq20)
    if key in _COUNT_CACHE:
        return _COUNT_CACHE[key]
    return scan_seq20(seq20, fasta)[0]


def scan_seq20(seq20: str, fasta: Path, max_sites: int = MAX_SITES) -> Tuple[OfftargetProfile, List[dict]]:
    """脱靶分档 + 位点明细（坐标、链、错配数、错配位置、比对序列、CFD/MIT 评分）。

    位点列表按发现顺序截断到 max_sites（计数不受影响，始终全量精确）；
    同一基因组位点双链均合格时计两行（与 Cas-OFFinder 行计数口径一致）。
    结果进程内缓存（计数与位点明细共享同一次扫描，重复查询不重扫全基因组）；
    返回缓存副本，调用方就地补注释（区域/风险）不会污染缓存。
    """
    seq20 = seq20.upper()
    key = (_cache_key(fasta), seq20, max_sites)
    cached = _SITE_CACHE.get(key)
    if cached is None:
        profile, sites = _scan_seq20(seq20, fasta, collect_sites=True, max_sites=max_sites)
        _SITE_CACHE[key] = (profile, sites)
        _COUNT_CACHE[(_cache_key(fasta), seq20)] = profile
    else:
        profile, sites = cached
    return profile, [dict(s) for s in sites]


def _site_record(
    seq20: str,
    chrom: str,
    g0: int,
    strand: str,
    pam: str,
    win_codes: np.ndarray,
    mm_idx: np.ndarray,
) -> dict:
    """构造单个脱靶位点明细（坐标 1-based 闭区间，错配位置按 gRNA 方向 1-based）。"""
    from backend.app.services.cfd_score import cfd_site_score, mit_hit_score

    win_bases = BASES_ASCII[win_codes].tobytes().decode("ascii")
    if strand == "+":
        protospacer = win_bases
        mismatch_positions = [int(i) + 1 for i in mm_idx]
    else:
        protospacer = _revcomp(win_bases)
        mismatch_positions = [WINDOW - int(i) for i in mm_idx]

    return {
        "chrom": chrom,
        "start": g0 + 1,
        "end": g0 + WINDOW,
        "strand": strand,
        "protospacer20": protospacer,
        "pam": pam,
        "mismatch_count": int(mm_idx.size),
        "mismatch_positions": mismatch_positions,
        "cfd_score": round(cfd_site_score(seq20, protospacer), 6),
        "mit_hit_score": round(mit_hit_score(seq20, protospacer), 4),
    }


def _scan_seq20(
    seq20: str, fasta: Path, collect_sites: bool, max_sites: int = MAX_SITES
) -> Tuple[OfftargetProfile, List[dict]]:
    """全基因组脱靶扫描核心：分档计数（始终）+ 位点明细（可选）。"""
    seq20 = seq20.upper()
    if len(seq20) != WINDOW or any(b not in b"ACGT" for b in seq20.encode()):
        raise ValueError(f"seq20 必须为 20nt ACGT: {seq20!r}")

    p1 = LUT[np.frombuffer(seq20.encode(), dtype=np.uint8)]
    p2 = LUT[np.frombuffer(_revcomp(seq20).encode(), dtype=np.uint8)]
    block_codes = _pattern_block_codes(p1) + _pattern_block_codes(p2)

    total_exact = total_mis1 = total_mis2 = total_mis3 = 0
    sites: List[dict] = []
    for rec in _load_fai(fasta):
        chrom = rec[0]
        length = rec[1]
        n_total = length - (WINDOW - 1)
        for s in range(0, max(n_total, 0), CHUNK_BASES):
            n_windows = min(CHUNK_BASES, n_total - s)
            if n_windows <= 0:
                break
            fetch_start = max(s - PAD_BEFORE, 0)
            raw = _fetch(fasta, rec, fetch_start, s + n_windows + PAD_AFTER)
            t = LUT[np.frombuffer(raw, dtype=np.uint8)]
            c = _pack_codes(t)
            w0 = s - fetch_start  # 首个计数窗口在 t 中的下标

            mask = np.zeros(n_windows, dtype=bool)
            for o, bc in block_codes:
                mask |= c[w0 + o : w0 + o + n_windows] == bc

            starts = np.flatnonzero(mask) + w0
            if starts.size == 0:
                continue

            # 行合格性：正链行 = 窗口后 2bp 为 GG（PAM NGG）；负链行 = 窗口前 2bp 为 CC（正链读作 CCN）
            # 仅对下标合法的窗口读 PAM 碱基：染色体末端 fetch 会被截断，越界花式索引会抛
            # IndexError（曾在全基因组末端命中时让整批导出静默降级为"未计算"）
            g = starts.astype(np.int64) + fetch_start
            p1_elig = np.zeros(starts.size, dtype=bool)
            p2_elig = np.zeros(starts.size, dtype=bool)
            ok1 = (g + 22 < length) & (starts + 22 < t.size)
            ok2 = (g >= 3) & (starts >= 3)
            if ok1.any():
                s1 = starts[ok1]
                p1_elig[ok1] = (t[s1 + 21] == CODE_G) & (t[s1 + 22] == CODE_G)
            if ok2.any():
                s2 = starts[ok2]
                p2_elig[ok2] = (t[s2 - 3] == CODE_C) & (t[s2 - 2] == CODE_C)

            idx = np.flatnonzero(p1_elig | p2_elig)
            ar = np.arange(WINDOW)
            for i in range(0, idx.size, VERIFY_BATCH):
                sel = idx[i : i + VERIFY_BATCH]
                wins = t[starts[sel][:, None] + ar[None, :]]
                for pat, elig_arr, strand in ((p1, p1_elig, "+"), (p2, p2_elig, "-")):
                    e = elig_arr[sel]
                    if not e.any():
                        continue
                    mm_all = wins != pat[None, :]
                    h_all = mm_all.sum(axis=1)
                    h = h_all[e]
                    bc = np.bincount(h, minlength=4)
                    total_exact += int(bc[0])
                    total_mis1 += int(bc[1])
                    total_mis2 += int(bc[1] + bc[2])
                    total_mis3 += int(bc[1] + bc[2] + bc[3])
                    if collect_sites and len(sites) < max_sites:
                        g_sel = g[sel]
                        t_sel = starts[sel]
                        for r in np.flatnonzero(e):
                            hh = int(h_all[r])
                            if hh > 3 or len(sites) >= max_sites:
                                continue
                            tl = int(t_sel[r])
                            if strand == "+":
                                pam_nt = BASES_ASCII[t[tl + 20]]
                            else:
                                pam_nt = BASES_ASCII[COMP_CODE[t[tl - 1]]]
                            pam = bytes([int(pam_nt)]).decode("ascii") + "GG"
                            sites.append(
                                _site_record(
                                    seq20, chrom, int(g_sel[r]), strand, pam,
                                    wins[r], np.flatnonzero(mm_all[r]),
                                )
                            )
    profile = OfftargetProfile(exact=total_exact, mis1=total_mis1, mis2=total_mis2, mis3=total_mis3)
    return profile, sites


def compute_offtarget_profiles(seq20s: Iterable[str], genome_fasta: Path | None = None) -> Dict[str, OfftargetProfile]:
    """对唯一 seq20 批量分档计数；返回 {seq20: OfftargetProfile}。基因组缺失时抛异常由调用方降级。

    多 guide 并行扫描（numpy 比较释放 GIL）；进程内按 (基因组, seq20) 记忆，
    同一 guide 不重复扫描。
    """
    fasta = genome_fasta or resolve_genome_fasta()
    if not fasta.exists():
        raise FileNotFoundError(f"T2T 基因组 FASTA 不存在: {fasta}")

    uniq = list(dict.fromkeys(s.upper() for s in seq20s))
    out: Dict[str, OfftargetProfile] = {
        s: _COUNT_CACHE[(_cache_key(fasta), s)] for s in uniq if (_cache_key(fasta), s) in _COUNT_CACHE
    }
    todo = [s for s in uniq if s not in out]
    if todo:
        with ThreadPoolExecutor(max_workers=min(4, len(todo))) as pool:
            for s, p in zip(todo, pool.map(lambda x: profile_seq20(x, fasta), todo)):
                out[s] = p
                _COUNT_CACHE[(_cache_key(fasta), s)] = p
                logger.info("脱靶分档完成 %s: mis3=%d exact=%d", s, p.mis3, p.exact)
    return out


def compute_offtarget_counts(seq20s: Iterable[str], genome_fasta: Path | None = None) -> Dict[str, int]:
    """兼容包装：返回 {seq20: mis3}。"""
    return {s: p.mis3 for s, p in compute_offtarget_profiles(seq20s, genome_fasta).items()}


def peek_profiles(seq20s: Iterable[str], genome_fasta: Path) -> Dict[str, OfftargetProfile]:
    """仅读进程内已扫描缓存，绝不触发全基因组扫描（快导出复用按需计算产物）。"""
    out: Dict[str, OfftargetProfile] = {}
    for s in seq20s:
        p = _COUNT_CACHE.get((_cache_key(genome_fasta), s.upper()))
        if p is not None:
            out[s.upper()] = p
    return out
