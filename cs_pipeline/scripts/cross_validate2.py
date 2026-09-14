"""修正版：检测文件格式（文本/二进制xls），解析 USR-8145 与 USR-23709"""
import re, glob, os

RAW = r"d:\lifesciencechallenge\cs_pipeline\data\raw"

def is_text(p):
    with open(p, "rb") as f:
        head = f.read(64)
    return not head.startswith(b"\xd0\xcf\x11\xe0")  # OLE2 magic

def parse_blocks_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    blocks = []
    for i, l in enumerate(lines):
        m = re.match(r"^\t?(\d{3})-(\S+?)[\t\s]", l)
        if m:
            blocks.append((i, m.group(1), m.group(2)))
    out = []
    for i, (ln, num, ref) in enumerate(blocks):
        end = blocks[i+1][0] if i+1 < len(blocks) else len(lines)
        total = left_nonwt = 0; nhap = 0
        for l in lines[ln+1:end]:
            f = l.split("\t")
            if len(f) > 5 and f[2].strip().isdigit():
                n = int(f[2].strip()); total += n; nhap += 1
                if f[4].strip() != "WT":
                    left_nonwt += n
        out.append((num, ref, total, left_nonwt, left_nonwt/total if total else 0, nhap))
    return out

for pat in ["*8145*", "*23709*"]:
    files = sorted(set(glob.glob(os.path.join(RAW, "**", pat), recursive=True)))
    for p in files:
        if not os.path.isfile(p) or not p.lower().endswith((".xls", ".txt")):
            continue
        print("=" * 70)
        print(p, os.path.getsize(p), "文本" if is_text(p) else "二进制OLE")
        if not is_text(p):
            continue
        blocks = parse_blocks_text(p)
        print(f"  块数: {len(blocks)}")
        for num, ref, total, lnw, pct, nhap in blocks:
            flag = " <<<100%" if pct == 1.0 else ""
            print(f"  块{num} {ref:20s} reads={total:6d} 单倍型={nhap:3d} 左非WT={lnw:5d} -> {pct:.4f}{flag}")
