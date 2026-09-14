"""修正: reads行无前导tab -> f[1]=reads, f[3]=Ltype"""
import re, os

RAW = r"d:\lifesciencechallenge\cs_pipeline\data\raw"

def parse_text_blocks(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    blocks = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{3})-(\S+)$", l.strip())
        if m:
            blocks.append((i, m.group(1), m.group(2).strip()))
    out = []
    for j, (ln, num, ref) in enumerate(blocks):
        end = blocks[j+1][0] if j+1 < len(blocks) else len(lines)
        total = left_nonwt = 0; nhap = 0
        for l in lines[ln+1:end]:
            f = l.split("\t")
            if len(f) > 4 and f[1].strip().isdigit():
                n = int(f[1].strip()); total += n; nhap += 1
                if f[3].strip() != "WT":
                    left_nonwt += n
        out.append((num, ref, total, left_nonwt, left_nonwt/total if total else 0, nhap))
    return out

print("USR-8145 CPT1/CPT2 块097-112:")
b = parse_text_blocks(os.path.join(RAW, "hitom", "all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls"))
for num, ref, total, lnw, pct, nhap in b:
    if ref in ("refCPT1", "refCPT2"):
        flag = " <<<" if pct == 1.0 else ""
        print(f"  块{num} {ref:8s} reads={total:5d} 单倍型={nhap} 左非WT={lnw:5d} -> {pct:.4f}{flag}")

print("\nUSR-23709 块001-069:")
b2 = parse_text_blocks(os.path.join(RAW, "consolidation_sources", "all-SY12100-USR-23709-Hi-TOM-sequencing-result_original.xls"))
for num, ref, total, lnw, pct, nhap in b2:
    mark = " <<<TKS_0184" if num == "037" else ""
    print(f"  块{num} {ref:18s} reads={total:5d} 单倍型={nhap} 左非WT={lnw:5d} -> {pct:.4f}{mark}")
