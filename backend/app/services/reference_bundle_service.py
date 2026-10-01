"""参考包（ReferenceBundle）注册、解析与证据加载（D1）。

参考包 = 参考基因组 FASTA（必需） + GFF 基因注释（可选） + 表达矩阵（可选）+ 组织列映射。
- 预置包 `lettuce`（莴苣 LsT2T；表达证据在库内 gene_expressions）与 `tks`（橡胶草；
  S1–S9 时相矩阵，evm.TU↔evm.model 规则映射）由代码定义，不落库；
- 用户导入包经「服务端路径注册」写入 reference_bundles 表（D2 导入管线调用 register_bundle）。

口径纪律：缺证据即返回 None 并给出缺失原因，绝不编造数值。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import ReferenceBundle

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = _REPO_ROOT / "cs_pipeline" / "data" / "reference_genomes"

TKS_GENOME_FASTA = REFERENCE_DIR / "2-1_TKS.genome.fasta"
TKS_GFF = REFERENCE_DIR / "2-2_TKS.genome.gff3"
_TKS_EXPR_XLSX = _REPO_ROOT / "cs_pipeline" / "data" / "expression" / "2-3_TKS_Tiss-Dev-Expression(1).xlsx"
_TKS_TISSUE_CODES = {"根": "gen", "叶": "ye", "胶乳": "jiaoru", "花": "hua", "花葶": "huating"}
_TKS_WINDOW_NOTE = "S4（方案6 产胶通路推荐转化窗口）"

# PROMOTER_UPSTREAM（启动子窗口不变量）已随区域分类归一迁至 gene_structure_service 单点定义。


@dataclass
class ResolvedBundle:
    """解析后的参考包（预置或导入统一形态）。"""

    id: str
    display_name: str
    kind: str  # preset | imported
    fasta: Optional[Path]
    gene_source: str  # db（库内 genes 表） | gff（包内 GFF）
    gff: Optional[Path] = None
    expression_path: Optional[Path] = None
    expression_layout: str = "none"  # db | tissue_tpm | stage_tissue | none
    expression_id_rule: str = "same"  # same | evm_tu_to_model
    tissue_columns: Dict[str, str] = field(default_factory=dict)
    notes: Optional[str] = None


# ---------------------------------------------------------------- .fai 索引

def ensure_fai(fasta: Path) -> Path:
    """确保 FASTA 有 .fai 索引；缺失时纯 Python 构建（免 samtools 依赖）。"""
    fai = Path(str(fasta) + ".fai")
    if fai.exists():
        return fai
    entries: List[Tuple[str, int, int, int, int]] = []
    name: Optional[str] = None
    length = offset = linebases = linewidth = 0
    pos = 0
    with open(fasta, "rb") as fh:
        for line in fh:
            if line.startswith(b">"):
                if name is not None:
                    entries.append((name, length, offset, linebases, linewidth))
                name = line[1:].split()[0].decode("utf-8", "ignore")
                length = offset = linebases = linewidth = 0
            else:
                stripped = line.rstrip(b"\r\n")
                if name is None:
                    raise ValueError(f"FASTA 格式错误：首个记录前出现序列行: {fasta}")
                if length == 0:
                    offset = pos
                    linebases = len(stripped)
                    linewidth = len(line)
                length += len(stripped)
            pos += len(line)
    if name is not None:
        entries.append((name, length, offset, linebases, linewidth))
    if not entries:
        raise ValueError(f"FASTA 无任何序列记录: {fasta}")
    with open(fai, "w", encoding="utf-8") as fh:
        for n, ln, off, lb, lw in entries:
            fh.write(f"{n}\t{ln}\t{off}\t{lb}\t{lw}\n")
    logger.info("已构建 FASTA 索引 %s（%d 条记录）", fai, len(entries))
    return fai


# ---------------------------------------------------------------- GFF 基因索引

_gff_cache: Dict[str, Dict[str, List[dict]]] = {}


def load_gff_gene_index(gff: Path) -> Dict[str, List[dict]]:
    """GFF3 gene 特征 → {chrom: [{"gene_id","start","end","strand"}, ...]}（按 start 排序，进程内缓存）。

    记录形状与 gene_structure_service.classify_gene_records 的回退适配器输入一致。
    """
    key = str(gff)
    if key in _gff_cache:
        return _gff_cache[key]
    idx: Dict[str, List[dict]] = {}
    with open(gff, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9 or parts[2] != "gene":
                continue
            gene_id = "gene"
            for kv in parts[8].split(";"):
                if kv.startswith("ID="):
                    gene_id = kv[3:]
                    break
            idx.setdefault(parts[0], []).append(
                {"gene_id": gene_id, "start": int(parts[3]), "end": int(parts[4]), "strand": parts[6]}
            )
    for lst in idx.values():
        lst.sort(key=lambda r: r["start"])
    _gff_cache[key] = idx
    return idx


# ---------------------------------------------------------------- 表达矩阵

_expr_cache: Dict[str, object] = {}


def _load_expr_frame(path: Path):
    """lazy 加载表达矩阵（csv/xlsx），索引为小写基因 ID；进程内按路径缓存。"""
    key = str(path)
    if key in _expr_cache:
        return _expr_cache[key]
    df = None
    try:
        import pandas as pd

        if path.suffix.lower() in (".xlsx", ".xls"):
            raw = pd.read_excel(path)
        else:
            raw = pd.read_csv(path)
        id_col = raw.columns[0]
        raw[id_col] = raw[id_col].astype(str).str.lower()
        df = raw.set_index(id_col)
    except Exception as exc:
        logger.warning("表达矩阵加载失败 %s: %s", path, exc)
        df = None
    _expr_cache[key] = df
    return df


def _match_expr_row(df, gene_id: str, id_rule: str):
    """按 id_rule 定位表达行；无证据返回 None（不编造）。"""
    key = str(gene_id).lower()
    if id_rule == "evm_tu_to_model":
        locus = key.split(".", 2)[-1] if key.startswith("evm.") else key
        key = f"evm.model.{locus}"
    if key in df.index:
        row = df.loc[key]
        matched_id = key
    else:
        lowered = {str(i).lower(): i for i in df.index}
        if key not in lowered:
            return None, None
        row = df.loc[lowered[key]]
        matched_id = str(lowered[key])
    if hasattr(row, "iloc") and getattr(row, "ndim", 1) > 1:
        row = row.iloc[0]
    return row, matched_id


def expression_tpm(bundle: ResolvedBundle, gene_id: str) -> Optional[Dict[str, float]]:
    """tissue_tpm 布局：{组织名: TPM}；无矩阵/无证据/非同口径布局返回 None。"""
    if bundle.expression_layout != "tissue_tpm" or bundle.expression_path is None:
        return None
    df = _load_expr_frame(bundle.expression_path)
    if df is None:
        return None
    row, _ = _match_expr_row(df, gene_id, bundle.expression_id_rule)
    if row is None:
        return None
    out: Dict[str, float] = {}
    for label, col in bundle.tissue_columns.items():
        if col in df.columns and row[col] == row[col]:
            out[label] = float(row[col])
    return out or None


def expression_stage_peaks(bundle: ResolvedBundle, gene_id: str) -> Optional[Dict[str, float]]:
    """stage_tissue 布局：每组织取 S1–S9 时相峰值 TPM（label → 各时相重复均值的最大值）。

    方案3 表达项的 TKS 口径聚合规则（已确认：不加权、时相取峰值）；无证据的组织不出现（表达项按 0）。
    """
    if bundle.expression_layout != "stage_tissue" or bundle.expression_path is None:
        return None
    df = _load_expr_frame(bundle.expression_path)
    if df is None:
        return None
    row, _ = _match_expr_row(df, gene_id, bundle.expression_id_rule)
    if row is None:
        return None

    import re as _re

    out: Dict[str, float] = {}
    for label, code in bundle.tissue_columns.items():
        best: Optional[float] = None
        for stage in range(1, 10):
            pat = _re.compile(rf"^S{stage}-{_re.escape(code)}(-\d+)?$")
            cols = [c for c in df.columns if pat.match(str(c))]
            vals = [float(row[c]) for c in cols if row[c] == row[c]]
            if vals:
                m = sum(vals) / len(vals)
                best = m if best is None or m > best else best
        if best is not None:
            out[label] = best
    return out or None


def stage_expression_block(bundle: ResolvedBundle, gene_id: str) -> Optional[dict]:
    """stage_tissue 布局（橡胶草 S1–S9 时相）：阶段 × 关键组织重复均值摘要。"""
    if bundle.expression_layout != "stage_tissue" or bundle.expression_path is None:
        return None
    df = _load_expr_frame(bundle.expression_path)
    if df is None:
        return None
    row, matched_id = _match_expr_row(df, gene_id, bundle.expression_id_rule)
    if row is None:
        return None

    import re as _re

    stage_means: Dict[str, Dict[str, float]] = {}
    for stage in range(1, 10):
        per_tissue: Dict[str, float] = {}
        for label, code in bundle.tissue_columns.items():
            pat = _re.compile(rf"^S{stage}-{_re.escape(code)}(-\d+)?$")
            cols = [c for c in df.columns if pat.match(str(c))]
            vals = [float(row[c]) for c in cols if row[c] == row[c]]
            if vals:
                per_tissue[code] = round(sum(vals) / len(vals), 2)
        if per_tissue:
            stage_means[f"S{stage}"] = per_tissue
    if not stage_means:
        return None

    def _peak(tissue_code: str) -> Optional[str]:
        cand = {s: v.get(tissue_code) for s, v in stage_means.items() if v.get(tissue_code) is not None}
        return max(cand, key=cand.get) if cand else None

    latex_code = bundle.tissue_columns.get("胶乳", "jiaoru")
    root_code = bundle.tissue_columns.get("根", "gen")
    return {
        "matched_id": matched_id,
        "stage_means": stage_means,
        "peak_stage_latex": _peak(latex_code),
        "peak_stage_root": _peak(root_code),
        "recommended_window": bundle.notes or _TKS_WINDOW_NOTE,
        "evidence_note": (
            "时相表达证据来自橡胶草 S1–S9 多组织表达矩阵（evm.TU↔evm.model 规则映射，36,239/36,239 一一对应）；"
            "方案3 组织优先指数的表达项取各组织 S1–S9 时相峰值 TPM（不加权、非单点 TPM），"
            "与莴苣单点 TPM 口径不可互比。"
        ),
    }


# ---------------------------------------------------------------- 预置包 / 注册

def _preset_bundle(bundle_id: str) -> Optional[ResolvedBundle]:
    if bundle_id == "lettuce":
        from backend.app.services import offtarget_service

        fasta = offtarget_service.resolve_genome_fasta()
        gff = REFERENCE_DIR / "3-1_LsT2T.annotation.gff3"
        return ResolvedBundle(
            id="lettuce",
            display_name="莴苣 (LsT2T)",
            kind="preset",
            fasta=fasta if fasta.exists() else None,
            gene_source="db",
            gff=gff if gff.exists() else None,
            expression_layout="db",
        )
    if bundle_id == "tks":
        return ResolvedBundle(
            id="tks",
            display_name="橡胶草 (TKS)",
            kind="preset",
            fasta=TKS_GENOME_FASTA if TKS_GENOME_FASTA.exists() else None,
            gene_source="gff",
            gff=TKS_GFF if TKS_GFF.exists() else None,
            expression_path=_TKS_EXPR_XLSX if _TKS_EXPR_XLSX.exists() else None,
            expression_layout="stage_tissue",
            expression_id_rule="evm_tu_to_model",
            tissue_columns=dict(_TKS_TISSUE_CODES),
            notes=_TKS_WINDOW_NOTE,
        )
    return None


def _row_to_bundle(row: ReferenceBundle) -> ResolvedBundle:
    tissue_columns: Dict[str, str] = {}
    if row.tissue_columns:
        try:
            tissue_columns = dict(json.loads(row.tissue_columns))
        except Exception:
            logger.warning("参考包 %s 的 tissue_columns 不是合法 JSON，按空处理", row.id)
    return ResolvedBundle(
        id=row.id,
        display_name=row.display_name,
        kind="imported",
        fasta=Path(row.fasta_path) if row.fasta_path else None,
        gene_source="gff" if row.gff_path else "none",
        gff=Path(row.gff_path) if row.gff_path else None,
        expression_path=Path(row.expression_path) if row.expression_path else None,
        expression_layout=row.expression_layout or "none",
        expression_id_rule=row.expression_id_rule or "same",
        tissue_columns=tissue_columns,
        notes=row.notes,
    )


async def resolve_bundle(db: Optional[AsyncSession], bundle_id: str) -> ResolvedBundle:
    """bundle_id → ResolvedBundle。预置包优先，其次导入包表；未知 ID 抛 KeyError。"""
    bid = (bundle_id or "lettuce").strip()
    preset = _preset_bundle(bid)
    if preset is not None:
        return preset
    if db is not None:
        row = (
            await db.execute(select(ReferenceBundle).where(ReferenceBundle.id == bid))
        ).scalar_one_or_none()
        if row is not None:
            return _row_to_bundle(row)
    raise KeyError(f"未知参考包 ID: {bundle_id}")


async def list_bundles(db: AsyncSession) -> List[dict]:
    """预置包 + 导入包清单（含证据可用性，如实标注）。"""
    out: List[dict] = []
    for bid in ("lettuce", "tks"):
        b = _preset_bundle(bid)
        out.append(bundle_summary(b))
    rows = (await db.execute(select(ReferenceBundle).order_by(ReferenceBundle.id))).scalars().all()
    out.extend(bundle_summary(_row_to_bundle(r)) for r in rows)
    return out


def bundle_summary(b: ResolvedBundle) -> dict:
    return {
        "id": b.id,
        "display_name": b.display_name,
        "kind": b.kind,
        "fasta_available": bool(b.fasta and b.fasta.exists()),
        "gff_available": bool(b.gff and b.gff.exists()),
        "expression_available": bool(b.expression_path and b.expression_path.exists()),
        "expression_layout": b.expression_layout,
        "expression_id_rule": b.expression_id_rule,
        "gene_source": b.gene_source,
        "tissue_columns": b.tissue_columns,
        "notes": b.notes,
    }


def validate_import_paths(
    fasta_path: Path,
    gff_path: Optional[Path],
    expression_path: Optional[Path],
    tissue_columns: Optional[Dict[str, str]],
) -> None:
    """导入前置校验：路径存在、FASTA 可建 .fai、表达矩阵可解析且映射列存在。失败抛 ValueError。"""
    if not fasta_path.exists():
        raise ValueError(f"参考基因组 FASTA 不存在: {fasta_path}")
    ensure_fai(fasta_path)
    if gff_path is not None and not gff_path.exists():
        raise ValueError(f"GFF 文件不存在: {gff_path}")
    if expression_path is not None:
        if not expression_path.exists():
            raise ValueError(f"表达矩阵不存在: {expression_path}")
        df = _load_expr_frame(expression_path)
        if df is None:
            raise ValueError(f"表达矩阵无法解析（需 csv/xlsx，首列为基因 ID）: {expression_path}")
        missing = [c for c in (tissue_columns or {}).values() if c not in df.columns]
        if missing:
            raise ValueError(
                f"表达矩阵缺少映射列: {missing}；实际列样例: {list(df.columns)[:8]}"
            )


async def register_bundle(
    db: AsyncSession,
    bundle_id: str,
    display_name: str,
    fasta_path: str,
    gff_path: Optional[str] = None,
    expression_path: Optional[str] = None,
    tissue_columns: Optional[Dict[str, str]] = None,
    expression_id_rule: str = "same",
    notes: Optional[str] = None,
    allow_overwrite: bool = False,
) -> dict:
    """服务端路径注册参考包（D2 导入管线入口）。校验通过后落库，返回包摘要。"""
    bid = bundle_id.strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", bid):
        raise ValueError("参考包 ID 须为小写字母/数字/下划线/连字符（1-63 位）")
    if _preset_bundle(bid) is not None:
        raise ValueError(f"{bid} 为内置预置包 ID，不允许覆盖；请换一个 ID")

    def _resolve(p: Optional[str]) -> Optional[Path]:
        if not p:
            return None
        path = Path(p)
        return path if path.is_absolute() else (_REPO_ROOT / path)

    fasta = _resolve(fasta_path)
    gff = _resolve(gff_path)
    expr = _resolve(expression_path)
    validate_import_paths(fasta, gff, expr, tissue_columns)

    existing = (
        await db.execute(select(ReferenceBundle).where(ReferenceBundle.id == bid))
    ).scalar_one_or_none()
    if existing is not None:
        if not allow_overwrite:
            raise ValueError(f"参考包 ID 已存在: {bid}（如需覆盖请显式确认）")
        row = existing
    else:
        row = ReferenceBundle(id=bid)
        db.add(row)

    row.display_name = display_name or bid
    row.fasta_path = str(fasta)
    row.gff_path = str(gff) if gff else None
    row.expression_path = str(expr) if expr else None
    row.expression_layout = "tissue_tpm" if (expr and tissue_columns) else "none"
    row.expression_id_rule = expression_id_rule
    row.tissue_columns = json.dumps(tissue_columns or {}, ensure_ascii=False)
    row.notes = notes
    await db.commit()
    return bundle_summary(_row_to_bundle(row))
