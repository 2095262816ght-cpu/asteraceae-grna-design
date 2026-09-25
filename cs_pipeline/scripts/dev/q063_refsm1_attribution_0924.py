# -*- coding: utf-8 -*-
"""q063_refsm1_attribution_0924.py — `063-refsm1` 块切点归属复核（质询文档第二、四节的全部数字）。

配套文档：results/query_063refsm1_attribution_0924.md
用途：供计B 独立复核"表记 guide 归属与读段级切点证据不一致"这一发现，不必采信质询文档的转述。

运行（在 cs_pipeline/ 下，crispr 或任意带 pandas 的环境，约 3 秒；**不需要 WSL / fastq**）：
    python scripts/dev/q063_refsm1_attribution_0924.py

方法要点（两处踩过的坑，已在下方注释标出）：
  1. Hi-TOM 导出的 .xls 实为 TSV，块以整行 `NNN-refXXX` 为组头，向下读到下一个 `^\\d+-ref` 为止；
  2. 变异位点 = 该行 reads seq 中**小写字母**的下标；
  3. ⚠️ 定位 guide 必须用该块 `Left/Right variation type` 均为 WT 的那一行，**不能用第一行**——
     063 块第一行本身带 1bp 插入且正落在 guide B 的原间隔内，用它会得出"B 不存在"的错误结论；
  4. 切点 = 原间隔起点 +17（+链命中）/ +3（−链命中），即 Cas9 切于 PAM 上游 3bp。
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent.parent.parent
HITOM = (BASE / "data/raw/hitom/NEWdata_0918/02_HiTOM结果表格/USR-6883-SY3382"
         / "all-SY3382-USR-6883-Hi-TOM-sequencing-result.xls")
BLOCK = "063-refsm1"

GUIDE_A = "GGCGTTAGATTGACAGAAGA"   # 主表 TKS_1313 的 seq-20，备注"guide确定"
GUIDE_B = "GTAGCCGGCGGCATCTATAT"   # guide候选 sheet 中 refsm1 的 候选1，热点得分 220356
TABLE_INDEL_PCT = 0.9090           # 主表 data/1_Hi-results-16.1-efficiency-20260921.xlsx
WINDOWS = (3, 5, 6, 8, 10, 15)


def rc(s):
    return s.translate(str.maketrans("ACGTacgt", "TGCAtgca"))[::-1]


def read_block(path, name):
    """按块号精确取块。同一 ref 在单批次内可有多达 29 个块，故必须按块号而非 ref 名定位。"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hits = [k for k, l in enumerate(lines) if l.strip() == name]
    assert len(hits) == 1, f"块 {name} 命中 {len(hits)} 次，期望 1 次"
    rows = []
    for line in lines[hits[0] + 1:]:
        if re.match(r"^\s*\d+-ref", line):
            break
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def variant_positions(read_seq):
    """Hi-TOM 用小写字母标记与参考的差异，取其下标即变异位点。"""
    return [m.start() for m in re.finditer("[acgt]", read_seq)]


def locate_cut_sites(wt_left, wt_right):
    """在 WT 读段中定位两条 guide 的原间隔与推算切点。"""
    sites = {}
    for name, guide in (("A", GUIDE_A), ("B", GUIDE_B)):
        for side, seq in (("L", wt_left.upper()), ("R", wt_right.upper())):
            for strand, target in (("+", guide), ("-", rc(guide).upper())):
                k = seq.find(target)
                if k >= 0:
                    cut = k + 17 if strand == "+" else k + 3
                    sites.setdefault(name, []).append((side, cut, strand, k))
    return sites


def attribute(rows, sites, window):
    """按窗口把每个非 WT 行归到 A / B / 双切 / 未归属，返回各自读段数。"""
    att = {"A": 0, "B": 0, "both": 0, "far": 0}
    for r in rows:
        n = int(r[1])
        if r[3] == "WT" and r[4] == "WT":
            continue
        hit = set()
        for side, seq in (("L", r[7]), ("R", r[8])):
            for pos in variant_positions(seq):
                for name, cuts in sites.items():
                    if any(s == side and abs(pos - c) <= window for s, c, _, _ in cuts):
                        hit.add(name)
        att["both" if len(hit) > 1 else (next(iter(hit)) if hit else "far")] += n
    return att


def main():
    assert HITOM.exists(), f"找不到 Hi-TOM 导出：{HITOM}"
    rows = read_block(HITOM, BLOCK)
    total = sum(int(r[1]) for r in rows)
    wt_reads = sum(int(r[1]) for r in rows if r[3] == "WT" and r[4] == "WT")
    non_wt = total - wt_reads

    print("=== 第二节：原始数据 ===")
    print("文件：%s" % HITOM.relative_to(BASE))
    print("块 %s：%d 个变异行，总读段 %d" % (BLOCK, len(rows), total))
    print("%-3s %-7s %-8s %-9s %-9s %-14s %s"
          % ("#", "Reads", "Ratio", "Left型", "Right型", "Left位点", "Right位点"))
    for r in rows:
        print("%-3s %-7s %-8s %-9s %-9s %-14s %s"
              % (r[0], r[1], r[2], r[3], r[4],
                 variant_positions(r[7])[:6], variant_positions(r[8])[:6]))
    print()
    print("WT 读段 %d/%d = %.4f → 非 WT = %.4f" % (wt_reads, total, wt_reads / total, non_wt / total))
    print("主表 TKS_1313 的 indel_pct = %.4f" % TABLE_INDEL_PCT)
    assert abs(non_wt / total - TABLE_INDEL_PCT) < 5e-5, \
        "非 WT 占比与主表 indel_pct 不符，indel_pct = 非WT读段占比 这一确证不成立"
    print("→ 二者一致：确证 indel_pct 的定义就是「该块非 WT 读段占比」")

    wt_row = next(r for r in rows if r[3] == "WT" and r[4] == "WT")
    sites = locate_cut_sites(wt_row[7], wt_row[8])
    print()
    print("=== 第三节：两条 guide 的定位（参考读段取自 WT 行，左读段全长 %d）===" % len(wt_row[7]))
    for name in ("A", "B"):
        for side, cut, strand, k in sites.get(name, []):
            print("  guide %s：%s 读段 %s 链命中于 %d–%d → 推算切点 %s≈%d"
                  % (name, side, strand, k, k + 19, side, cut))
        if name not in sites:
            print("  guide %s：**在 WT 读段中未命中**" % name)

    print()
    print("=== 第四节：窗口敏感性（占全部 %d 读段的比例）===" % total)
    print("%-6s %-10s %-10s %-10s %s" % ("窗口", "guide A", "guide B", "双切", "未归属"))
    for w in WINDOWS:
        a = attribute(rows, sites, w)
        print("±%-5d %-10.4f %-10.4f %-10.4f %.4f"
              % (w, a["A"] / total, a["B"] / total, a["both"] / total, a["far"] / total))
    print()
    print("结论：guide A 的独占归属在 ±3…±15 的任何窗口下都是 0.0000；")
    print("      窗口 ±6 时 guide B 覆盖 %.4f，恰等于全部非 WT 读段。" % (
        attribute(rows, sites, 6)["B"] / total))
    print()
    print("以上为质询文档 results/query_063refsm1_attribution_0924.md 第二、三、四节的全部数字。")


if __name__ == "__main__":
    main()
