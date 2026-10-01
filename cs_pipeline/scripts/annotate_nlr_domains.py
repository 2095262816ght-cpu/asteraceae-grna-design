"""NLR 蛋白功能域注释最小路线（教师反馈 #3）。

对目标 NLR 基因（±2kb 侧翼）运行 NLR-Annotator v2.1b（cs_pipeline/tools/nlr-annotator，
Steuernagel et al., Plant Physiology 2020），将 CC/TIR/NBS/LRR 结构域命中映射回基因组坐标，
产出 cs_pipeline/data/reference_genomes/domain_annotations.csv（gene_structure_service 旁路表）。

基因清单来源（择一）：
- lifescience.db genes 表 nlr_type='NLR-LRR'（主界面基因 ID 口径）；
- cs_pipeline/demo/app_genes.csv（演示口径，经 GFF overlap 解析出基因 ID）。

用法：
  python -m cs_pipeline.scripts.annotate_nlr_domains            # 默认全量 49 个 NLR 基因
  python -m cs_pipeline.scripts.annotate_nlr_domains --limit 3  # 调试
"""
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services import offtarget_service as ot  # noqa: E402
from backend.app.services import gene_structure_service as gs  # noqa: E402

NLR_TOOL_DIR = REPO_ROOT / "cs_pipeline" / "tools" / "nlr-annotator"
OUT_CSV = REPO_ROOT / "cs_pipeline" / "data" / "reference_genomes" / "domain_annotations.csv"
LOCI_CSV = REPO_ROOT / "cs_pipeline" / "data" / "reference_genomes" / "nlr_gene_loci.csv"
DEMO_GENES_CSV = REPO_ROOT / "cs_pipeline" / "demo" / "app_genes.csv"
DEMO_CANDIDATES_CSV = REPO_ROOT / "cs_pipeline" / "data" / "demo" / "demo_nlr50_candidates.csv"
GFF = REPO_ROOT / "cs_pipeline" / "data" / "reference_genomes" / "3-1_LsT2T.annotation.gff3"
WORK_DIR = REPO_ROOT / "_scratch" / "nlr_annotator_run"
FLANK = 2000

# NLR-Annotator motif → 结构域分类（官方 AnnotatorSignatureDefinition.loadDefaultMotifCategories）
MOTIF_CATEGORY = {
    "motif_1": "NBARC", "motif_2": "NBARC", "motif_3": "NBARC", "motif_4": "NBARC",
    "motif_5": "NBARC", "motif_6": "NBARC", "motif_10": "NBARC", "motif_12": "NBARC",
    "motif_7": "LINKER", "motif_8": "LINKER",
    "motif_9": "LRR", "motif_11": "LRR", "motif_19": "LRR",
    "motif_13": "TIR", "motif_15": "TIR", "motif_18": "TIR",
    "motif_16": "CC", "motif_17": "CC",
    "motif_14": "NA", "motif_20": "NA",
}
CATEGORY_TO_DOMAIN = {"NBARC": "NBS", "LRR": "LRR", "TIR": "TIR", "CC": "CC"}


def load_nlr_genes_from_db() -> List[dict]:
    db_path = REPO_ROOT / "lifescience.db"
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = db.execute(
        "select gene_id, chrom, start, end, strand from genes where nlr_type='NLR-LRR'"
    ).fetchall()
    db.close()
    return [
        {"gene_id": r[0], "chrom": r[1], "start": int(r[2]), "end": int(r[3]), "strand": r[4]}
        for r in rows
    ]


def load_nlr_genes_from_demo_csv() -> List[dict]:
    out = []
    with open(DEMO_GENES_CSV, "r", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("nlr_type") != "NLR-LRR":
                continue
            out.append({
                "gene_id": r["gene_id"],
                "chrom": r["g_chrom"],
                "start": int(r["g_start"]),
                "end": int(r["g_end"]),
                "strand": r["g_strand"],
            })
    return out


def resolve_gff_gene_id(chrom: str, start: int, end: int) -> Optional[str]:
    """坐标 → GFF 基因 ID（取重叠最多的基因）。"""
    genes = gs.load_gff_structure(GFF)
    best, best_ov = None, 0
    norm = {chrom, "Chr" + str(int(chrom[3:])) if chrom[:3].lower() == "chr" and chrom[3:].isdigit() else chrom}
    for gid, g in genes.items():
        if g["chrom"] not in norm:
            continue
        ov = min(end, g["end"]) - max(start, g["start"]) + 1
        if ov > best_ov:
            best, best_ov = gid, ov
    return best


def remap_gene_loci(genes: List[dict], fasta: Path, samples_per_gene: int = 5) -> List[dict]:
    """demo 坐标 → LsT2T 参考基因组坐标重定位。

    49 个 NLR demo 基因（LsaT2T* 命名空间）的坐标来自外部数据集的另一套组装，
    与 3-1_LsT2T.genome.fa 存在固定偏移。用候选 seq30 在参考基因组上精确重定位
    （find_many_seq30_in_genome），按基因取偏移中位数换算基因窗口。
    返回带 remap_chrom/start/end/offset 的基因列表（原字段保留）。
    """
    from backend.app.services.sequence_annotation_service import find_many_seq30_in_genome

    cand = pd.read_csv(DEMO_CANDIDATES_CSV)
    seq30_by_gene: Dict[str, List[dict]] = {}
    for r in cand.itertuples():
        seq30_by_gene.setdefault(r.gene_id, []).append(r)

    all_seqs: List[str] = []
    plan: Dict[str, List[str]] = {}
    for g in genes:
        rows = seq30_by_gene.get(g["gene_id"], [])[:samples_per_gene]
        seqs = [r.seq30 for r in rows]
        plan[g["gene_id"]] = seqs
        all_seqs.extend(seqs)
    print(f"重定位 {len(all_seqs)} 条候选 seq30（{len(plan)} 个基因）……")
    hits = find_many_seq30_in_genome(list(dict.fromkeys(all_seqs)), fasta)

    out = []
    for g in genes:
        offsets = []
        hit_coords = []
        for r in seq30_by_gene.get(g["gene_id"], []):
            if r.seq30 not in plan[g["gene_id"]]:
                continue
            h = hits.get(r.seq30)
            if not h:
                continue
            # 候选 start/end 为 23nt（guide+PAM）窗口；hit 为 30nt 窗口，guide 起点 = hit.start+4
            offsets.append(int(r.start) - (h["start"] + 4))
            hit_coords.append(h)
        if not offsets:
            print(f"[skip] {g['gene_id']} 无法重定位（候选 seq30 未命中参考基因组）")
            continue
        offsets.sort()
        offset = offsets[len(offsets) // 2]
        chrom = hit_coords[0]["chrom"]
        ng = dict(g)
        ng["offset"] = offset
        ng["remap_chrom"] = chrom
        ng["remap_start"] = g["start"] - offset
        ng["remap_end"] = g["end"] - offset
        out.append(ng)
        print(f"  {g['gene_id']}: 偏移 {offset:+d} → {chrom}:{ng['remap_start']}-{ng['remap_end']}")
    return out


def extract_regions(genes: List[dict], fasta: Path) -> List[dict]:
    """±FLANK 侧翼提取区域序列（优先重定位坐标），写 WORK_DIR/regions.fa；返回区域元数据。"""
    recs = {r[0]: r for r in ot._load_fai(fasta)}
    regions = []
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORK_DIR / "regions.fa", "w", encoding="utf-8") as fh:
        for g in genes:
            chrom = g.get("remap_chrom", g["chrom"])
            gstart = g.get("remap_start", g["start"])
            gend = g.get("remap_end", g["end"])
            rec = recs.get(chrom)
            if rec is None:
                for alt in ("Chr" + str(int(chrom[3:])) if chrom[:3].lower() == "chr" and chrom[3:].isdigit() else None,
                            chrom.replace("Chr", "chr")):
                    if alt and alt in recs:
                        rec = recs[alt]
                        break
            if rec is None:
                print(f"[skip] 基因组无染色体 {chrom}: {g['gene_id']}")
                continue
            lo = max(1, gstart - FLANK)
            hi = min(rec[1], gend + FLANK)
            seq = ot._fetch(fasta, rec, lo - 1, hi).decode("ascii", "ignore").upper()
            reg_id = f"{g['gene_id']}|{rec[0]}|{lo}|{hi}"
            fh.write(f">{reg_id}\n")
            for i in range(0, len(seq), 60):
                fh.write(seq[i : i  + 60] + "\n")
            regions.append({"reg_id": reg_id, "gene_id": g["gene_id"], "chrom": rec[0], "lo": lo, "hi": hi})
    return regions


def run_nlr_annotator() -> Tuple[Path, Path, Path]:
    out_tsv = WORK_DIR / "nlr_out.tsv"
    out_gff = WORK_DIR / "nlr_out.gff"
    out_motifs = WORK_DIR / "nlr_motifs.bed"
    cmd = [
        "java", "-jar", str(NLR_TOOL_DIR / "NLR-Annotator-v2.1b.jar"),
        "-i", str(WORK_DIR / "regions.fa"),
        "-x", str(NLR_TOOL_DIR / "mot.txt"),
        "-y", str(NLR_TOOL_DIR / "store.txt"),
        "-o", str(out_tsv),
        "-g", str(out_gff),
        "-m", str(out_motifs),
        "-t", "4",
    ]
    print("运行:", " ".join(cmd))
    subprocess.run(cmd, check=True, timeout=3600)
    return out_tsv, out_gff, out_motifs


def parse_motif_bed(out_motifs: Path, regions: List[dict]) -> List[dict]:
    """motifs.bed → 基因组坐标 motif 命中（BED 0-based 半开区间）。"""
    by_id = {r["reg_id"]: r for r in regions}
    hits = []
    with open(out_motifs, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            seqname, s, e, motif, _score, strand = parts[:6]
            reg = by_id.get(seqname)
            if reg is None:
                continue
            s0, e0 = int(s), int(e)  # 0-based 半开
            if strand == "-":
                g_start, g_end = reg["hi"] - e0 + 1, reg["hi"] - s0
            else:
                g_start, g_end = reg["lo"] + s0, reg["lo"] + e0 - 1
            cat = MOTIF_CATEGORY.get(motif, "NA")
            hits.append({
                "gene_id": reg["gene_id"],
                "chrom": reg["chrom"],
                "start": g_start,
                "end": g_end,
                "strand": strand if strand in "+-" else "+",
                "motif": motif,
                "category": cat,
                "domain_type": CATEGORY_TO_DOMAIN.get(cat, "Other"),
            })
    return hits


def normalize_domain_type(name: str) -> str:
    cat = MOTIF_CATEGORY.get(name, "")
    return CATEGORY_TO_DOMAIN.get(cat, "Other")


def parse_gff_hits(out_gff: Path, regions: List[dict]) -> List[dict]:
    """NLR-Annotator GFF → 基因组坐标命中（含负链坐标换算）。"""
    by_id = {r["reg_id"]: r for r in regions}
    hits = []
    with open(out_gff, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            seqname, _src, feature, start, end, _score, strand, _frame, attr = parts[:9]
            reg = by_id.get(seqname)
            if reg is None:
                continue
            rel_start, rel_end = int(start), int(end)
            if strand == "-":
                # 负链命中：输入序列反向互补坐标 → 基因组
                g_start = reg["hi"] - rel_end + 1
                g_end = reg["hi"] - rel_start + 1
            else:
                g_start = reg["lo"] + rel_start - 1
                g_end = reg["lo"] + rel_end - 1
            # 属性里的 motif/特征名
            name = ""
            for kv in attr.split(";"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k.lower() in ("name", "motif", "id", "note", "feature"):
                        name = v
                        break
            hits.append({
                "gene_id": reg["gene_id"],
                "chrom": reg["chrom"],
                "start": g_start,
                "end": g_end,
                "strand": strand if strand in "+-" else "+",
                "feature": feature,
                "motif": name or feature,
                "domain_type": normalize_domain_type(name or feature),
            })
    return hits


def merge_domains(hits: List[dict]) -> List[dict]:
    """同基因同类型相邻/重叠命中合并为结构域区间（间隙 ≤ 120bp）。"""
    merged: List[dict] = []
    for key in sorted({(h["gene_id"], h["strand"], h["domain_type"]) for h in hits}):
        gene_id, strand, dtype = key
        group = sorted(
            [h for h in hits if (h["gene_id"], h["strand"], h["domain_type"]) == key],
            key=lambda h: h["start"],
        )
        cur = dict(group[0])
        for h in group[1:]:
            if h["start"] - cur["end"] <= 300:
                cur["end"] = max(cur["end"], h["end"])
                cur["motif"] = f"{cur['motif']},{h['motif']}" if cur["motif"] != h["motif"] else cur["motif"]
            else:
                merged.append(cur)
                cur = dict(h)
        merged.append(cur)
    return merged


def load_loci_from_csv() -> List[dict]:
    """从 nlr_gene_loci.csv 复用重定位结果（--reuse-loci）。"""
    out = []
    with open(LOCI_CSV, "r", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({
                "gene_id": r["gene_id"],
                "chrom": r["orig_chrom"],
                "start": int(r["orig_start"]),
                "end": int(r["orig_end"]),
                "strand": "+",
                "offset": int(r["offset"]) if r.get("offset") else 0,
                "remap_chrom": r["remap_chrom"],
                "remap_start": int(r["remap_start"]),
                "remap_end": int(r["remap_end"]),
            })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="仅处理前 N 个基因（调试）")
    ap.add_argument("--from-demo-csv", action="store_true", help="从 demo/app_genes.csv 读基因清单")
    ap.add_argument("--reuse-loci", action="store_true",
                    help="复用已有 nlr_gene_loci.csv 的重定位结果（跳过全基因组 seq30 重定位）")
    args = ap.parse_args()

    fasta = ot.resolve_genome_fasta()
    if args.reuse_loci and LOCI_CSV.exists():
        genes = load_loci_from_csv()
        print(f"复用重定位表 {LOCI_CSV}（{len(genes)} 个基因）")
    else:
        genes = []
        if not args.from_demo_csv:
            try:
                genes = load_nlr_genes_from_db()
            except Exception as exc:
                print(f"[warn] 读 DB 失败（{exc}），改用 demo/app_genes.csv")
        if not genes:
            genes = load_nlr_genes_from_demo_csv()
        genes = remap_gene_loci(genes, fasta)
    if args.limit:
        genes = genes[: args.limit]
    print(f"NLR 目标基因 {len(genes)} 个")

    regions = extract_regions(genes, fasta)
    print(f"提取区域 {len(regions)} 个 → {WORK_DIR / 'regions.fa'}")

    out_tsv, out_gff, out_motifs = run_nlr_annotator()
    hits = parse_motif_bed(out_motifs, regions)
    print(f"NLR-Annotator motif 命中 {len(hits)} 条")

    # gene_id 保持库内/演示命名空间（LsaT2T*），供界面按基因 ID 查询；
    # GFF 命名空间映射写入 nlr_gene_loci.csv 供结构回查
    loci_rows = []
    for g in genes:
        gff_id = resolve_gff_gene_id(g.get("remap_chrom", g["chrom"]),
                                     g.get("remap_start", g["start"]),
                                     g.get("remap_end", g["end"]))
        loci_rows.append({
            "gene_id": g["gene_id"],
            "orig_chrom": g["chrom"], "orig_start": g["start"], "orig_end": g["end"],
            "remap_chrom": g.get("remap_chrom", ""), "remap_start": g.get("remap_start", ""),
            "remap_end": g.get("remap_end", ""), "offset": g.get("offset", ""),
            "gff_gene_id": gff_id or "",
        })
    with open(LOCI_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(loci_rows[0].keys()) if loci_rows else
                           ["gene_id", "orig_chrom", "orig_start", "orig_end",
                            "remap_chrom", "remap_start", "remap_end", "offset", "gff_gene_id"])
        w.writeheader()
        for row in loci_rows:
            w.writerow(row)
    print(f"写出 {LOCI_CSV}（{len(loci_rows)} 个基因重定位）")

    domains = merge_domains(hits)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gene_id", "transcript_id", "chrom", "start", "end", "strand",
                    "domain_type", "domain_name", "source"])
        for d in sorted(domains, key=lambda d: (d["gene_id"], d["start"])):
            w.writerow([d["gene_id"], "", d["chrom"], d["start"], d["end"], d["strand"],
                        d["domain_type"], d["motif"][:120],
                        "NLR-Annotator-2.1b (motif×category, Steuernagel 2020)"])
    print(f"写出 {OUT_CSV}（{len(domains)} 个结构域区间）")


if __name__ == "__main__":
    main()
