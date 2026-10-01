"""基因结构注释：GFF 外显子/内含子/CDS/TSS 解析 + 位点区域判定 + 蛋白功能域旁路表。

- 解析 GFF3 层级（gene → mRNA → exon/CDS，兼容 GFF2 风格 gene_id/transcript_id 属性），
  按基因聚合外显子/CDS 区间并推导 TSS（链感知：+ 链取基因起点、- 链取基因终点）；
- classify_position 将基因组坐标判为 exon / intron / promoter(TSS 上游链感知窗口) / intergenic；
- 蛋白功能域来自旁路注释表 domain_annotations.csv（GFF 不含结构域信息，
  由 NLR-Annotator / HMMER 离线注释产出，见 cs_pipeline/tools/nlr-annotator/），
  缺表时 domains 如实为空，不编造。
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.services.reference_bundle_service import REFERENCE_DIR

logger = logging.getLogger(__name__)

# 启动子/TSS 上游窗口（bp）：区域分类不变量，随本模块（区域分类唯一属主）单点定义。
# 原先散在 reference_bundle_service 与调用方字面量（offtarget 硬编码 2000、注释"2kb"）。
PROMOTER_UPSTREAM = 2000

DOMAIN_ANNOTATIONS_CSV = REFERENCE_DIR / "domain_annotations.csv"
NLR_GENE_LOCI_CSV = REFERENCE_DIR / "nlr_gene_loci.csv"

# gene_id -> record
_structure_cache: Dict[str, Dict[str, dict]] = {}
_domains_cache: Optional[List[dict]] = None
_loci_cache: Optional[Dict[str, dict]] = None


def _parse_attrs(attr: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for kv in attr.strip().split(";"):
        kv = kv.strip()
        if not kv or "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        out[k.strip()] = v.strip().strip('"')
    return out


def load_gff_structure(gff: Path) -> Dict[str, dict]:
    """GFF → {gene_id: {chrom, start, end, strand, tss, exons, cds, transcripts}}（进程内缓存）。

    exons/cds 为基因级并集（按 start 排序的 (start, end) 1-based 闭区间列表）。
    """
    key = str(gff)
    if key in _structure_cache:
        return _structure_cache[key]

    genes: Dict[str, dict] = {}
    tx_gene: Dict[str, str] = {}
    tx_exons: Dict[str, List[Tuple[int, int]]] = {}
    tx_cds: Dict[str, List[Tuple[int, int]]] = {}

    with open(gff, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9:
                continue
            ftype = parts[2]
            if ftype not in ("gene", "mRNA", "transcript", "exon", "CDS"):
                continue
            chrom, start, end, strand, attr = parts[0], int(parts[3]), int(parts[4]), parts[6], parts[8]
            attrs = _parse_attrs(attr)

            if ftype == "gene":
                gid = attrs.get("ID") or attrs.get("gene_id") or attrs.get("Name")
                if not gid:
                    continue
                genes[gid] = {
                    "gene_id": gid,
                    "chrom": chrom,
                    "start": start,
                    "end": end,
                    "strand": strand,
                    "tss": start if strand == "+" else end,
                    "exons": [],
                    "cds": [],
                    "transcripts": [],
                }
            elif ftype in ("mRNA", "transcript"):
                tid = attrs.get("ID") or attrs.get("transcript_id")
                parents = (attrs.get("Parent") or attrs.get("gene_id") or "").split(",")
                gid = parents[0] if parents else ""
                if tid and gid:
                    tx_gene[tid] = gid
                    if gid in genes:
                        genes[gid]["transcripts"].append(tid)
            else:  # exon / CDS
                parents = (attrs.get("Parent") or attrs.get("transcript_id") or "").split(",")
                bucket = tx_exons if ftype == "exon" else tx_cds
                for p in parents:
                    p = p.strip()
                    if p:
                        bucket.setdefault(p, []).append((start, end))

    for tid, exons in tx_exons.items():
        gid = tx_gene.get(tid)
        if gid in genes:
            genes[gid]["exons"].extend(exons)
    for tid, cds in tx_cds.items():
        gid = tx_gene.get(tid)
        if gid in genes:
            genes[gid]["cds"].extend(cds)

    for g in genes.values():
        g["exons"] = sorted(set(g["exons"]))
        g["cds"] = sorted(set(g["cds"]))

    logger.info("GFF 结构解析 %s：%d 个基因", gff.name, len(genes))
    _structure_cache[key] = genes
    return genes


def load_nlr_gene_loci() -> Dict[str, dict]:
    """NLR demo 基因重定位表（gene_id → 原坐标/重定位坐标/偏移/GFF 基因 ID）。"""
    global _loci_cache
    if _loci_cache is not None:
        return _loci_cache
    out: Dict[str, dict] = {}
    if NLR_GENE_LOCI_CSV.exists():
        try:
            with open(NLR_GENE_LOCI_CSV, "r", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    out[r.get("gene_id", "")] = r
        except Exception as exc:
            logger.warning("NLR 基因重定位表解析失败 %s: %s", NLR_GENE_LOCI_CSV, exc)
    _loci_cache = out
    return out


def gene_structure(gff: Path, gene_id: str) -> Optional[dict]:
    """单基因结构（含 TSS 与蛋白功能域旁路注释）；无该基因返回 None。

    49 个 NLR demo 基因（LsaT2T* 命名空间）坐标与参考基因组存在版本偏移，
    经 nlr_gene_loci.csv 重定位表映射到 GFF 基因结构，并如实标注坐标来源。
    """
    genes = load_gff_structure(gff)
    rec = genes.get(gene_id)
    coordinate_note = None
    if rec is None:
        loc = load_nlr_gene_loci().get(gene_id)
        if loc and loc.get("gff_gene_id") in genes:
            rec = genes[loc["gff_gene_id"]]
            coordinate_note = (
                f"该基因为 NLR demo 面板基因（{gene_id}），原始坐标 "
                f"{loc.get('orig_chrom')}:{loc.get('orig_start')}-{loc.get('orig_end')} 来自外部数据集组装版本，"
                f"与当前参考基因组存在偏移 {loc.get('offset')}bp；"
                f"此处结构为经候选序列重定位后的 {loc.get('remap_chrom')}:{loc.get('remap_start')}-{loc.get('remap_end')} "
                f"区间（GFF 基因 {loc.get('gff_gene_id')}）"
            )
    if rec is None:
        return None
    out = dict(rec)
    out["gene_id_query"] = gene_id
    out["coordinate_note"] = coordinate_note
    out["domains"] = [d for d in load_domain_annotations() if d.get("gene_id") == gene_id]
    return out


def load_domain_annotations() -> List[dict]:
    """蛋白功能域旁路表 domain_annotations.csv（可缺省，缺省返回 [] 不编造）。"""
    global _domains_cache
    if _domains_cache is not None:
        return _domains_cache
    rows: List[dict] = []
    if DOMAIN_ANNOTATIONS_CSV.exists():
        try:
            with open(DOMAIN_ANNOTATIONS_CSV, "r", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    rows.append({
                        "gene_id": r.get("gene_id", ""),
                        "transcript_id": r.get("transcript_id", ""),
                        "chrom": r.get("chrom", ""),
                        "start": int(r["start"]) if r.get("start") else None,
                        "end": int(r["end"]) if r.get("end") else None,
                        "strand": r.get("strand", ""),
                        "domain_type": r.get("domain_type", ""),
                        "domain_name": r.get("domain_name", ""),
                        "source": r.get("source", ""),
                    })
        except Exception as exc:
            logger.warning("功能域注释表解析失败 %s: %s", DOMAIN_ANNOTATIONS_CSV, exc)
            rows = []
    else:
        logger.info("功能域注释表不存在（可选）: %s", DOMAIN_ANNOTATIONS_CSV)
    _domains_cache = rows
    return rows


def norm_chroms(chrom: str) -> set:
    """染色体命名兼容集：Chr1 / Chr01 / chr1 互认（各数据源命名不统一）。"""
    chroms = {chrom, chrom.replace("chr", "Chr").replace("CHR", "Chr"), chrom.lstrip("Cc")}
    norm = set()
    for c in chroms:
        norm.add(c)
        if c[:3].lower() == "chr" and c[3:].isdigit():
            norm.add("Chr" + str(int(c[3:])))
    return norm


def _promoter_hit(strand: str, tss: int, pos: int) -> bool:
    """TSS 上游链感知窗口命中判定（PROMOTER_UPSTREAM 的唯一谓词）。"""
    if strand == "+":
        return tss - PROMOTER_UPSTREAM <= pos < tss
    if strand == "-":
        return tss < pos <= tss + PROMOTER_UPSTREAM
    return False


def classify_position(genes: Dict[str, dict], chrom: str, pos: int) -> Tuple[str, Optional[str]]:
    """坐标区域判定：(region_type, gene_id)。GFF 外显子粒度适配器。

    优先级：exon > intron > promoter（TSS 上游链感知 PROMOTER_UPSTREAM 窗口）> intergenic。
    chrom 命名兼容 Chr1 / Chr01 / chr1。
    """
    norm = norm_chroms(chrom)
    best_promoter: Optional[str] = None
    for gid, g in genes.items():
        if g["chrom"] not in norm:
            continue
        if g["start"] <= pos <= g["end"]:
            for s, e in g["exons"]:
                if s <= pos <= e:
                    return "exon", gid
            return "intron", gid
        if best_promoter is None and _promoter_hit(g["strand"], g["tss"], pos):
            best_promoter = gid
    if best_promoter:
        return "promoter", best_promoter
    return "intergenic", None


def classify_gene_records(
    records_by_chrom: Dict[str, List[dict]], chrom: str, pos: int
) -> Tuple[str, Optional[dict]]:
    """坐标区域判定：(region_type, record)。无外显子粒度数据源的回退适配器。

    供库内 genes 表（DB 适配器）与 GFF gene 索引共用：优先级
    基因体（无外显子粒度，按基因跨度近似标 exon）> TSS 上游 PROMOTER_UPSTREAM 链感知
    窗口（promoter）> intergenic。record 为 {gene_id, start, end, strand} 字典。
    """
    norm = norm_chroms(chrom)
    best_promoter: Optional[dict] = None
    for c in norm:
        for rec in records_by_chrom.get(c) or ():
            if int(rec["start"]) <= pos <= int(rec["end"]):
                return "exon", rec
            tss = int(rec["start"]) if rec["strand"] == "+" else int(rec["end"])
            if best_promoter is None and _promoter_hit(rec["strand"], tss, pos):
                best_promoter = rec
    if best_promoter is not None:
        return "promoter", best_promoter
    return "intergenic", None


REGION_LABELS = {
    "exon": "外显子 (exon)",
    "intron": "内含子 (intron)",
    "promoter": "启动子/TSS 上游 (promoter)",
    "intergenic": "基因间区 (intergenic)",
}
