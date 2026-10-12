"""解析 USR-25902 原始文件全部块头 + 每块非WT比例（统一口径: 左侧非WT reads/总reads）"""
import re
from pathlib import Path

path = str(Path(__file__).resolve().parents[1] / "data" / "raw" / "consolidation_sources" / "all-SY13249-USR-25902-Hi-TOM-sequencing-result_original.xls")
with open(path, "r", encoding="utf-8", errors="replace") as fh:
    lines = fh.read().splitlines()

# 块头: 形如 \t001-ref18265gene1\t...
blocks = []
for i, l in enumerate(lines):
    m = re.match(r"^\t(\d{3})-(\S+?)\t", l)
    if m:
        blocks.append((i, m.group(1), m.group(2)))
print("总块数:", len(blocks))
for i, (ln, num, ref) in enumerate(blocks):
    # 该块的 reads 行直到下一个块头
    end = blocks[i+1][0] if i+1 < len(blocks) else len(lines)
    total = 0
    left_nonwt = 0
    for l in lines[ln+1:end]:
        f = l.split("\t")
        # f: ['', sort, reads, ratio, Ltype, Rtype, ...]
        if len(f) > 5 and f[2].strip().isdigit():
            n = int(f[2].strip())
            total += n
            if f[4].strip() != "WT":
                left_nonwt += n
    pct = left_nonwt/total if total else 0
    print(f"  块{num} {ref:20s} 总reads={total:6d} 左侧非WT={left_nonwt:5d} -> {pct:.4f}")
