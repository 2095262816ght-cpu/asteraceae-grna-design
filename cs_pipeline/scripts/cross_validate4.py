"""最终验证:
1. USR-8145 块097-112 编辑率复算（验证100%行为真实高深度纯合编辑）
2. USR-23709 块037 (TKS_0184 离群0.5151) 复算
3. USR-8145 文件有无 096/8146 线索
4. USR-5712 批 fastq 存在性 + Sheet1 中该批 indel 复算
"""
import re, os, glob

RAW = r"d:\lifesciencechallenge\cs_pipeline\data\raw"

def parse_text_blocks(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    blocks = []
    for i, l in enumerate(lines):
        m = re.match(r"^(\d{3})-(\S+?)\s*$", l.strip()) or re.match(r"^\t?(\d{3})-([^\t]+?)\t", l)
        if m:
            blocks.append((i, m.group(1), m.group(2).strip()))
    out = []
    for j, (ln, num, ref) in enumerate(blocks):
        end = blocks[j+1][0] if j+1 < len(blocks) else len(lines)
        total = left_nonwt = 0; nhap = 0
        for l in lines[ln+1:end]:
            f = l.split("\t")
            if len(f) > 5 and f[2].strip().isdigit():
                n = int(f[2].strip()); total += n; nhap += 1
                if f[4].strip() != "WT":
                    left_nonwt += n
        out.append((num, ref, total, left_nonwt, left_nonwt/total if total else 0, nhap))
    return out

print("="*70)
print("USR-8145 块097-112 (CPT1=LG01.6995拷贝, CPT2=LG01.6999拷贝):")
b = parse_text_blocks(os.path.join(RAW, "hitom", "all-SY4070-USR-8145-Hi-TOM-sequencing-result.xls"))
for num, ref, total, lnw, pct, nhap in b:
    print(f"  块{num} {ref:6s} reads={total:5d} 单倍型={nhap} 左非WT={lnw:5d} -> {pct:.4f}")

print()
print("USR-23709 全部块 (找块037=TKS_0184):")
b2 = parse_text_blocks(os.path.join(RAW, "consolidation_sources", "all-SY12100-USR-23709-Hi-TOM-sequencing-result_original.xls"))
print("  块数:", len(b2))
for num, ref, total, lnw, pct, nhap in b2:
    if int(num) in (36, 37, 38):
        print(f"  块{num} {ref:18s} reads={total:5d} 单倍型={nhap} 左非WT={lnw:5d} -> {pct:.4f}")

print()
print("USR-8145 文件中所有 ref 名:")
print(" ", sorted(set(ref for _, ref, *_ in b)))
print("  块号范围:", min(n for n, *_ in b), "-", max(n for n, *_ in b))

print()
print("USR-5712 fastq 目录:")
d5712 = glob.glob(os.path.join(RAW, "hitom", "R1_sequencing", "2022-01-30", "**"), recursive=True)
for p in d5712[:10]:
    print(" ", p, "(dir)" if os.path.isdir(p) else os.path.getsize(p))
