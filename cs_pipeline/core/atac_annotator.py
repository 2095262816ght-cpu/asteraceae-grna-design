# -*- coding: utf-8 -*-
"""atac_annotator.py — ATAC-seq 染色质开放峰注释与可及性打分领域模块。

将 ATAC-seq peak 表（LettuceGDB 口径：Peak/Chr/Start/End/FoldChange/-log10(q-value)/gene/Effect type）
与候选 gRNA 坐标做区间匹配，产出可展示的表观注释列与 0–1 可及性分，
供推荐引擎（方案3 延伸）与批量导入注释使用。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# 峰边近端窗口（bp）：guide 中心距峰中心 ≤ 此值视为「峰近端」。
# 取 5kb：覆盖启动子/增强子—靶点常见调控距离量级；峰内仍为距离 0。
NEAR_BP = 5000

# 内部列名（展示层再映射中文）
COL_IN_PEAK = "atac_in_peak"
COL_PEAK_ID = "atac_peak_id"
COL_DIST = "atac_dist_bp"
COL_FC = "atac_fold_change"
COL_Q = "atac_neglog10q"
COL_SCORE = "atac_score"
COL_STATUS = "atac_status"

STATUS_IN_PEAK = "ATAC开放峰内"
STATUS_NEAR = "ATAC峰近端"
STATUS_FAR = "远离ATAC峰"
STATUS_NO_EVIDENCE = "无ATAC证据"

DISPLAY_MAP = {
    COL_IN_PEAK: "ATAC开放峰内",
    COL_PEAK_ID: "ATAC峰ID",
    COL_DIST: "ATAC距峰中心(bp)",
    COL_FC: "ATAC峰强度FC",
    COL_Q: "ATAC峰-log10(q)",
    COL_SCORE: "ATAC可及性分",
    COL_STATUS: "ATAC状态",
}

ANNOTATION_COLS = [COL_IN_PEAK, COL_PEAK_ID, COL_DIST, COL_FC, COL_Q, COL_SCORE, COL_STATUS]

# 展示层布尔→中文（是/否）映射：ATAC 注释的展示形态转换由 to_display_df 单点定义
DISPLAY_BOOL = {True: "是", False: "否"}


def to_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """ATAC 注释列的展示形态转换单点定义：DISPLAY_MAP 列名映射 + 峰内布尔列 → 是/否。

    demo Tab-2 批量流与 Tab-1 排序引擎共用本转换，不再各持一份副本。
    """
    out = df.rename(columns=DISPLAY_MAP)
    col = DISPLAY_MAP[COL_IN_PEAK]
    if col in out.columns:
        out[col] = out[col].map(DISPLAY_BOOL)
    return out

# 峰表列名归一化（兼容 LettuceGDB xlsx 与常见 BED/narrowPeak 导出）
_COL_ALIASES = {
    "peak": "peak_id",
    "peak_id": "peak_id",
    "peak_name": "peak_id",
    "chr": "chrom",
    "chrom": "chrom",
    "chromosome": "chrom",
    "start": "start",
    "end": "end",
    "stop": "end",
    "foldchange": "fold_change",
    "fold_change": "fold_change",
    "fold_enrichment": "fold_change",
    "foldchange_fc": "fold_change",
    "-log10(q-value)": "neglog10q",
    "neglog10q": "neglog10q",
    "-log10(qvalue)": "neglog10q",
    "qvalue": "neglog10q",
    "gene": "gene",
    "effect type": "effect_type",
    "effect_type": "effect_type",
}


@dataclass(frozen=True)
class AtacAtlas:
    """去重后的 ATAC 峰区间索引（按染色体分组，供区间/距离查询）。"""

    peaks: pd.DataFrame  # columns: peak_id, chrom, start, end, fold_change, neglog10q, gene, effect_type

    @property
    def n_peaks(self) -> int:
        return len(self.peaks)

    @property
    def chroms(self) -> list[str]:
        return sorted(self.peaks["chrom"].astype(str).unique().tolist())

    def _chrom_table(self, chrom: str) -> pd.DataFrame:
        return self.peaks[self.peaks["chrom"].astype(str) == str(chrom)]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {}
    for c in out.columns:
        key = str(c).strip().lower()
        if key in _COL_ALIASES:
            rename[c] = _COL_ALIASES[key]
    out = out.rename(columns=rename)
    required = {"chrom", "start", "end"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"ATAC 峰表缺少必要列: {sorted(missing)}（需 chrom/start/end）")
    if "peak_id" not in out.columns:
        out["peak_id"] = [f"peak_{i+1}" for i in range(len(out))]
    if "fold_change" not in out.columns:
        out["fold_change"] = np.nan
    if "neglog10q" not in out.columns:
        out["neglog10q"] = np.nan
    if "gene" not in out.columns:
        out["gene"] = ""
    if "effect_type" not in out.columns:
        out["effect_type"] = ""
    out["chrom"] = out["chrom"].astype(str).str.strip()
    out["start"] = pd.to_numeric(out["start"], errors="coerce").astype("Int64")
    out["end"] = pd.to_numeric(out["end"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["start", "end", "chrom"])
    out = out[out["end"] >= out["start"]]
    return out


def peaks_from_dataframe(raw: pd.DataFrame) -> AtacAtlas:
    """从任意峰表 DataFrame 构建 AtacAtlas（长表注释聚合到峰上，按区间去重）。"""
    df = _normalize_columns(raw)

    # 同一 Peak 多行（多 gene/effect type）合并为一行区间
    def _join_unique(s: pd.Series) -> str:
        vals = sorted({str(v).strip() for v in s.dropna() if str(v).strip()})
        return ",".join(vals)

    grouped = (
        df.groupby(["peak_id", "chrom", "start", "end"], as_index=False)
        .agg(
            fold_change=("fold_change", "first"),
            neglog10q=("neglog10q", "first"),
            gene=("gene", _join_unique),
            effect_type=("effect_type", _join_unique),
        )
    )
    grouped["start"] = grouped["start"].astype(int)
    grouped["end"] = grouped["end"].astype(int)
    return AtacAtlas(peaks=grouped.reset_index(drop=True))


def load_atac_peaks(path: Path | str) -> AtacAtlas:
    """从 .xlsx/.xls/.csv 载入 ATAC peak 表并按区间去重（长表注释聚合到峰上）。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"ATAC 峰表不存在: {path}")
    if path.suffix.lower() in {".xlsx", ".xls"}:
        raw = pd.read_excel(path)
    else:
        raw = pd.read_csv(path)
    return peaks_from_dataframe(raw)


def load_default_atac(base_dir: Path | str) -> AtacAtlas | None:
    """装载项目内置莴苣 ATAC 峰表；缺失时返回 None（优雅降级）。"""
    base = Path(base_dir)
    candidates = [
        base / "data" / "reference_genomes" / "1-3_Stem_lettuce_ATAC_peaks.xlsx",
        base / "data" / "reference_genomes" / "LettuceGDB_ATAC_peaks.xlsx",
    ]
    for p in candidates:
        if p.exists():
            return load_atac_peaks(p)
    return None


def _accessibility_score(in_peak: bool, dist_bp: float | None, fold_change: float | None) -> float:
    """0–1 可及性分：峰内按强度饱和计分，近端线性衰减，其余为 0。

    口径（透明可答辩）：
        峰内   : 0.6 + 0.4 * min(1, FC/10)   —— 开放且富集越强越高
        近端   : 0.3 * (1 - dist/NEAR_BP)    —— 峰缘 5kb 缓冲，随距离线性衰减
        其他   : 0                            —— 无开放证据不加分
    """
    if in_peak:
        fc = float(fold_change) if fold_change is not None and pd.notna(fold_change) else 1.0
        strength = min(1.0, max(0.0, fc) / 10.0)
        return round(0.6 + 0.4 * strength, 6)
    if dist_bp is not None and pd.notna(dist_bp) and dist_bp <= NEAR_BP:
        return round(0.3 * (1.0 - float(dist_bp) / NEAR_BP), 6)
    return 0.0


def annotate_guides(
    guides: pd.DataFrame,
    atlas: AtacAtlas,
    chrom_col: str = "chrom",
    start_col: str = "start",
    end_col: str = "end",
) -> pd.DataFrame:
    """为候选表追加 ATAC 注释列（原列完整保留）。

    需要 guide 行具备染色体与起止坐标；缺失坐标时相关列标记「无ATAC证据」。
    距离定义：guide 区间中心到最近 peak 中心的绝对距离；与 peak 区间重叠时距离记 0。
    """
    out = guides.copy()
    n = len(out)
    in_peak = np.zeros(n, dtype=bool)
    peak_ids: list[str | None] = [None] * n
    dists: list[float | None] = [None] * n
    fcs: list[float | None] = [None] * n
    qs: list[float | None] = [None] * n
    scores = np.zeros(n, dtype=float)
    status: list[str] = [STATUS_NO_EVIDENCE] * n

    has_coords = chrom_col in out.columns and start_col in out.columns and end_col in out.columns
    peaks = atlas.peaks
    by_chrom = {c: g for c, g in peaks.groupby("chrom", sort=False)}

    if has_coords:
        chrom_s = out[chrom_col].astype(str).str.strip()
        start_s = pd.to_numeric(out[start_col], errors="coerce")
        end_s = pd.to_numeric(out[end_col], errors="coerce")

        for i in range(n):
            chrom = chrom_s.iloc[i]
            if chrom in ("", "nan", "None") or pd.isna(start_s.iloc[i]) or pd.isna(end_s.iloc[i]):
                continue
            s0, e0 = int(start_s.iloc[i]), int(end_s.iloc[i])
            if e0 < s0:
                s0, e0 = e0, s0
            mid = (s0 + e0) // 2
            ctab = by_chrom.get(chrom)
            if ctab is None or ctab.empty:
                continue

            p_start = ctab["start"].to_numpy(dtype=np.int64)
            p_end = ctab["end"].to_numpy(dtype=np.int64)
            p_center = (p_start + p_end) // 2

            overlap = (p_start <= e0) & (p_end >= s0)
            if overlap.any():
                idx = np.flatnonzero(overlap)
                # 多峰重叠取 FoldChange 最高者
                fcv = ctab["fold_change"].to_numpy(dtype=float)
                best = idx[int(np.nanargmax(fcv[idx]))] if not np.all(np.isnan(fcv[idx])) else idx[0]
                row = ctab.iloc[int(best)]
                in_peak[i] = True
                peak_ids[i] = str(row["peak_id"])
                dists[i] = 0
                fcs[i] = float(row["fold_change"]) if pd.notna(row["fold_change"]) else None
                qs[i] = float(row["neglog10q"]) if pd.notna(row["neglog10q"]) else None
                status[i] = STATUS_IN_PEAK
            else:
                d = np.abs(p_center.astype(np.int64) - mid)
                best = int(np.argmin(d))
                row = ctab.iloc[best]
                dist_bp = int(d[best])
                peak_ids[i] = str(row["peak_id"])
                dists[i] = dist_bp
                fcs[i] = float(row["fold_change"]) if pd.notna(row["fold_change"]) else None
                qs[i] = float(row["neglog10q"]) if pd.notna(row["neglog10q"]) else None
                status[i] = STATUS_NEAR if dist_bp <= NEAR_BP else STATUS_FAR

            scores[i] = _accessibility_score(bool(in_peak[i]), dists[i], fcs[i])

    out[COL_IN_PEAK] = in_peak
    out[COL_PEAK_ID] = peak_ids
    out[COL_DIST] = dists
    out[COL_FC] = fcs
    out[COL_Q] = qs
    out[COL_SCORE] = scores
    out[COL_STATUS] = status
    return out


def detect_coord_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    """从任意表格智能探测 (chrom, start, end) 列名；探测不到返回 None。"""
    cols = list(df.columns)
    lower = {str(c).strip().lower(): c for c in cols}

    chrom = None
    for kw in ("chrom", "chr", "chromosome", "染色体"):
        for lk, orig in lower.items():
            if lk == kw or lk.startswith(kw):
                chrom = orig
                break
        if chrom:
            break

    start = None
    for kw in ("start", "start_pos", "startpos", "pos_start", "begin", "起点"):
        for lk, orig in lower.items():
            if lk == kw or lk.startswith(kw):
                # 避免误抓 end
                if "end" in lk and not lk.startswith("start"):
                    continue
                start = orig
                break
        if start:
            break

    end = None
    for kw in ("end", "end_pos", "endpos", "stop", "终点"):
        for lk, orig in lower.items():
            if lk == kw or lk.startswith(kw):
                end = orig
                break
        if end:
            break

    return chrom, start, end
