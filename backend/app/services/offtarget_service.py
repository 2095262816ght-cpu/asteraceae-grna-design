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
    """统计全基因组脱靶行数：20-mer 错配 1..3 且 PAM 为 NGG 的链特异行（完全匹配行不计）。"""
    seq20 = seq20.upper()
    if len(seq20) != WINDOW or any(b not in b"ACGT" for b in seq20.encode()):
        raise ValueError(f"seq20 必须为 20nt ACGT: {seq20!r}")

    p1 = LUT[np.frombuffer(seq20.encode(), dtype=np.uint8)]
    p2 = LUT[np.frombuffer(_revcomp(seq20).encode(), dtype=np.uint8)]
    block_codes = _pattern_block_codes(p1) + _pattern_block_codes(p2)

    total = 0
    for rec in _load_fai(fasta):
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
            g = starts.astype(np.int64) + fetch_start
            p1_elig = (g + 22 < length) & (t[starts + 21] == CODE_G) & (t[starts + 22] == CODE_G)
            p2_elig = (g >= 3) & (t[starts - 3] == CODE_C) & (t[starts - 2] == CODE_C)

            idx = np.flatnonzero(p1_elig | p2_elig)
            ar = np.arange(WINDOW)
            for i in range(0, idx.size, VERIFY_BATCH):
                sel = idx[i : i + VERIFY_BATCH]
                wins = t[starts[sel][:, None] + ar[None, :]]
                if p1_elig[sel].any():
                    h1 = (wins != p1[None, :]).sum(axis=1)
                    total += int(((h1 >= 1) & (h1 <= 3) & p1_elig[sel]).sum())
                if p2_elig[sel].any():
                    h2 = (wins != p2[None, :]).sum(axis=1)
                    total += int(((h2 >= 1) & (h2 <= 3) & p2_elig[sel]).sum())
    return total


def compute_offtarget_counts(seq20s: Iterable[str], genome_fasta: Path | None = None) -> Dict[str, int]:
    """对唯一 seq20 批量计数；返回 {seq20: count}。基因组缺失时抛异常由调用方降级。"""
    fasta = genome_fasta or resolve_genome_fasta()
    if not fasta.exists():
        raise FileNotFoundError(f"T2T 基因组 FASTA 不存在: {fasta}")

    uniq = list(dict.fromkeys(s.upper() for s in seq20s))
    out: Dict[str, int] = {}
    for s in uniq:
        out[s] = count_offtargets_for_seq20(s, fasta)
        logger.info("脱靶计数完成 %s: %d", s, out[s])
    return out
