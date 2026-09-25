# -*- coding: utf-8 -*-
"""recommendation_engine.py — 候选 gRNA 推荐与多组学决策引擎。

深度模块：将数据多表连接、模型版本列自适应、着丝粒/区域过滤、
多目标动态排序调度及表达证据状态解析全部封装于单一领域引擎。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

# 组织中英文对照
TISSUES = {"Root": "根", "Stem": "茎", "Leaf": "叶", "Flower": "花", "Seed": "种子"}
TISSUE_ORDER = list(TISSUES.keys())

EXPRESSION_STATUS_MAP = {
    "mapped": "已映射",
    "mapped_cluster": "已映射（串联簇）",
    "mapped_scaffold": "已映射（未挂载 scaffold）",
    "unmappable": "表达证据缺失",
}


@dataclass(frozen=True)
class GeneSummary:
    """指定靶基因的基础元数据摘要。"""
    gene_id: str
    chrom: str
    coords_text: str
    strand: str
    nlr_type: str
    total_candidates: int


@dataclass(frozen=True)
class ModelCallout:
    """模型版本与效率分定位说明。"""
    kind: str  # "success" | "warning" | "info"
    message: str


@dataclass(frozen=True)
class RankingResult:
    """推荐排序完整产物视图。"""
    top10_df: pd.DataFrame
    all_df: pd.DataFrame
    gene_summary: GeneSummary
    model_callout: ModelCallout
    has_offtarget: bool
    sort_options: list[str]
    elapsed_ms: float


class CandidateRankingEngine:
    """深度模块：管理候选 gRNA 检索、过滤、多组学属性合并与排序。"""

    def __init__(
        self,
        candidates_df: pd.DataFrame,
        genes_df: pd.DataFrame,
        priority_df: pd.DataFrame | None = None,
        hazard_df: pd.DataFrame | None = None,
    ):
        self._genes = genes_df.copy()
        
        # 合并多组学辅助表
        data = candidates_df.copy()
        if priority_df is not None:
            data = data.merge(priority_df, on="guide_id", how="left", validate="1:1")
        if hazard_df is not None:
            data = data.merge(hazard_df, on="guide_id", how="left", validate="1:1")
        self._data = data

        # 效率分列版本自适应
        self._has_offtarget = "offtarget_count_mis3" in self._data.columns and self._data["offtarget_count_mis3"].notna().any()
        self._has_v21 = "efficiency_score_v21_nob879" in self._data.columns and self._data["efficiency_score_v21_nob879"].notna().any()
        self._has_full = "efficiency_score_full_0916" in self._data.columns and self._data["efficiency_score_full_0916"].notna().any()
        self._has_stacking = self._has_v21 or self._has_full or ("efficiency_score" in self._data.columns and self._data["efficiency_score"].notna().any())

        if self._has_v21:
            self._eff_col = "efficiency_score_v21_nob879"
            self._eff_label = "效率分（v2.1排序参考）"
            self._callout = ModelCallout(
                kind="success",
                message="本页“效率分（v2.1排序参考）”用于**候选 guide 的相对排序与择优**（融合真实 DeepSpCas9、CRISPRon 及序列物理特征；2026-09-21 终版形态二分层模型，基于 noB879 纯 A 级金标准训练）。建议同一基因内取 top 3–5 条送实验终筛；分数为排序参考，非绝对突变率承诺（低混杂核心靶点上限 ρ=0.464，留出测试集 ρ=0.342）。"
            )
        elif self._has_full:
            self._eff_col = "efficiency_score_full_0916"
            self._eff_label = "效率分（Stacking排序参考）"
            self._callout = ModelCallout(
                kind="success",
                message="本页“效率分（Stacking预测）”用于**候选 guide 的相对排序**（融合 DeepSpCas9、CRISPRon 及序列物理特征；2026-09-16 全量数据重训版）。建议同一基因内取 top 3–5 条送实验终筛；分数为排序参考，非绝对效率承诺（模型 LOGO-CV ρ=0.414）。"
            )
        elif self._has_stacking:
            self._eff_col = "efficiency_score"
            self._eff_label = "效率分（Stacking排序参考）"
            self._callout = ModelCallout(
                kind="success",
                message="本页“效率分（Stacking预测）”为自主训练的 Stacking 集成模型预测分数（融合 DeepSpCas9、CRISPRon 及序列物理特征，反映 Hi-TOM 实测突变效率）。"
            )
        else:
            self._eff_col = "efficiency_placeholder"
            self._eff_label = "效率分（占位）"
            self._callout = ModelCallout(
                kind="warning",
                message="本页“效率分（占位）”列为序列启发式占位分（GC/Tm），**非模型预测**，待计A Stacking 模型接入后替换为真实预测分并重排序。"
            )

    @classmethod
    def load_from_directory(cls, base_dir: Path | str) -> CandidateRankingEngine:
        """从标准 demo 目录装载全量数据。"""
        base = Path(base_dir)
        cand_path = base / "demo" / "app_data.csv"
        genes_path = base / "demo" / "app_genes.csv"
        prio_path = base / "demo" / "app_data_tissue_priority.csv"
        haz_path = base / "results" / "offtarget_functional_hazard_0923.csv"

        cand_df = pd.read_csv(cand_path)
        genes_df = pd.read_csv(genes_path)

        prio_df = None
        if prio_path.exists():
            prio = pd.read_csv(prio_path)
            keep_p = [c for c in prio.columns if c.startswith(("priority_", "expr_sigmoid_", "expression_status", "lsa_id"))]
            prio_df = prio[["guide_id"] + keep_p]

        haz_df = None
        if haz_path.exists():
            h = pd.read_csv(haz_path)
            keep_h = [c for c in h.columns if c.startswith("hazard_")] + ["n_intra_panel_sites"]
            haz_df = h[["guide_id"] + keep_h]

        return cls(cand_df, genes_df, prio_df, haz_df)

    @property
    def genes(self) -> list[str]:
        """所有可选基因列表。"""
        return sorted(self._genes.gene_id.unique().tolist())

    @property
    def eff_label(self) -> str:
        return self._eff_label

    def get_sort_options(self, target_tissue: str) -> list[str]:
        """获取当前目标组织下的合法排序选项。"""
        tissue_cn = TISSUES.get(target_tissue, target_tissue)
        off_label = "脱靶计数 mis3 升序" if self._has_offtarget else "脱靶计数 mis3 升序（待数据）"
        return [
            f"组织优先指数（{tissue_cn}）降序（方案3推荐）",
            f"{self._eff_label} 降序",
            off_label,
            "GC% 接近 50%",
        ]

    def rank(
        self,
        gene_id: str,
        target_tissue: str = "Leaf",
        sort_key: str | None = None,
        region_types: Sequence[str] = ("promoter", "exon"),
        hide_centromere: bool = True,
    ) -> RankingResult:
        """执行指定基因的候选过滤与多组学融合推荐排序。"""
        t0 = time.perf_counter()

        # 基因元数据摘要
        g_rows = self._genes[self._genes.gene_id == gene_id]
        if g_rows.empty:
            raise KeyError(f"未找到基因 {gene_id}")
        ginfo = g_rows.iloc[0]

        # 候选筛选
        cand = self._data[self._data.gene_id == gene_id].copy()
        if hide_centromere and "in_centromere" in cand.columns:
            cand = cand[~cand.in_centromere]
        if region_types and "region_type" in cand.columns:
            cand = cand[cand.region_type.isin(region_types)]

        # 排序策略分发
        sort_opts = self.get_sort_options(target_tissue)
        selected_sort = sort_key or sort_opts[0]
        tissue_lower = target_tissue.lower()
        prio_col = f"priority_score_{tissue_lower}"
        haz_col = f"hazard_{tissue_lower}"

        if selected_sort.startswith("组织优先指数") and prio_col in cand.columns:
            cand = cand.sort_values(prio_col, ascending=False)
        elif selected_sort.startswith(self._eff_label) and self._eff_col in cand.columns:
            cand = cand.sort_values(self._eff_col, ascending=False)
        elif selected_sort.startswith("脱靶") and "offtarget_count_mis3" in cand.columns:
            cand = cand.sort_values("offtarget_count_mis3", ascending=True, na_position="last")
        elif "gc_pct" in cand.columns:
            cand = cand.assign(gc_dist=(cand.gc_pct - 50.0).abs()).sort_values("gc_dist")

        # 表达证据语义化标注
        if "expression_status" in cand.columns:
            cand["表达证据"] = cand["expression_status"].map(EXPRESSION_STATUS_MAP)

        # 格式化展示列名
        tissue_cn = TISSUES.get(target_tissue, target_tissue)
        prio_label = f"组织优先指数（{tissue_cn}）"
        haz_label = f"功能性脱靶危害（{tissue_cn}）"

        rename_map = {
            self._eff_col: self._eff_label,
            prio_col: prio_label,
            haz_col: haz_label,
            "n_intra_panel_sites": "面板内位点数",
            "offtarget_count_mis1": "脱靶 mis1",
            "offtarget_count_mis2": "脱靶 mis2",
            "offtarget_count_mis3": "脱靶 mis3",
            "exact_match_count": "完全匹配数",
            "in_centromere": "着丝粒区",
        }
        cand = cand.rename(columns=rename_map)

        show_cols = [
            "guide_id", "seq20", "pam", "chrom", "start", "end", "strand",
            "region_type", "gc_pct", "tm_c", self._eff_label, prio_label, haz_label,
            "面板内位点数", "表达证据",
            "脱靶 mis1", "脱靶 mis2", "脱靶 mis3", "完全匹配数", "着丝粒区",
        ]
        show_cols = [c for c in show_cols if c in cand.columns]
        view = cand[show_cols]

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        summary = GeneSummary(
            gene_id=gene_id,
            chrom=str(ginfo.get("g_chrom", "")),
            coords_text=f"{int(ginfo.get('g_start', 0)):,}–{int(ginfo.get('g_end', 0)):,}",
            strand=str(ginfo.get("g_strand", "")),
            nlr_type=str(ginfo.get("nlr_type", "—")),
            total_candidates=len(cand),
        )

        return RankingResult(
            top10_df=view.head(10),
            all_df=view,
            gene_summary=summary,
            model_callout=self._callout,
            has_offtarget=self._has_offtarget,
            sort_options=sort_opts,
            elapsed_ms=elapsed_ms,
        )
