"""分节解析 Hi-TOM 文件 + xlrd 读二进制"""
import re, glob, os

import os
RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

def parse_section(lines, lo, hi, label):
    print(f"  --- {label} 节 (行 {lo}~{hi}) ---")
    blocks = []
    for i in range(lo, min(hi, len(lines))):
        m = re.match(r"^\t?(\d{3})-(\S+?)[\t\s]", lines[i])
        if m:
            blocks.append((i, m.group(1), m.group(2)))
    for j, (ln, num, ref) in enumerate(blocks):
        end = blocks[j+1][0] if j+1 < len(blocks) else hi
        total = left_nonwt = 0; nhap = 0
        for l in lines[ln+1:end]:
            f = l.split("\t")
            if len(f) > 5 and f[2].strip().isdigit():
                n = int(f[2].strip()); total += n; nhap += 1
                if f[4].strip() != "WT":
                    left_nonwt += n
        pct = left_nonwt/total if total else 0
        flag = " <<<100%" if pct == 1.0 else ""
        print(f"  块{num} {ref:22s} reads={total:6d} 单倍型={nhap:3d} 左非WT={left_nonwt:5d} -> {pct:.4f}{flag}")

# ---- USR-8145 ----
p8145 = os.path.join(RAW, "hitom", "all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls")
with open(p8145, encoding="utf-8", errors="replace") as fh:
    lines = fh.read().splitlines()
print("="*70); print("USR-8145 总行数:", len(lines))
parse_section(lines, 0, 600, "前600行")

# ---- USR-23709 ----
p23709 = os.path.join(RAW, "consolidation_sources", "all-SY12100-USR-23709-Hi-TOM-sequencing-result_original.xls")
with open(p23709, encoding="utf-8", errors="replace") as fh:
    lines2 = fh.read().splitlines()
print("="*70); print("USR-23709 总行数:", len(lines2))
print("首3行:", [repr(l[:80]) for l in lines2[:3]])
parse_section(lines2, 0, len(lines2), "全文")
