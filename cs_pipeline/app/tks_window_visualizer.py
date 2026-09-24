# -*- coding: utf-8 -*-
"""橡胶草产胶时相决策组件（方案6），供 app/app.py Tab 1 调用。

数据来自 scripts/23 产物：
  results/tks_pathway_stage_curves_0923.csv（根 S1–S9 / 胶乳 S4–S9 家族均值曲线）
  results/tks_developmental_window_0923.csv（爆发期与推荐转化窗口卡）
  results/tks_rubber_family_members_0923.csv（同源筛选成员数）
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
CURVES = BASE / "results" / "tks_pathway_stage_curves_0923.csv"
WINDOW = BASE / "results" / "tks_developmental_window_0923.csv"
MEMBERS = BASE / "results" / "tks_rubber_family_members_0923.csv"

TISSUE_LABEL = {"gen": "根（gen）", "jiaoru": "胶乳（jiaoru）"}


@st.cache_data(show_spinner="加载橡胶草时相曲线…")
def _load():
    curves = pd.read_csv(CURVES)
    window = pd.read_csv(WINDOW).set_index("family")
    members = pd.read_csv(MEMBERS)
    curves["tissue_label"] = curves.tissue.map(TISSUE_LABEL)
    n_mem = members.groupby("family").tks_gene.nunique()
    return curves, window, n_mem


def render_tks_window() -> None:
    if not CURVES.exists():
        st.info("方案6 产物尚未生成：先运行 `python scripts/23_tks_developmental_window.py`。")
        return
    curves, window, n_mem = _load()
    fams = list(curves.family.unique())
    fam = st.selectbox(
        "橡胶生物合成基因家族",
        fams,
        format_func=lambda f: f"{f}（TKS 成员 {int(n_mem.get(f, 0))} 个）",
    )
    sub = curves[curves.family == fam]
    card = window.loc[fam]

    line = (
        alt.Chart(sub)
        .mark_line(point=True)
        .encode(
            x=alt.X("stage_num:Q", title="发育时相（S1–S9）",
                    scale=alt.Scale(domain=[1, 9])),
            y=alt.Y("mean_tpm:Q", title="mean TPM"),
            color=alt.Color("tissue_label:N", title=None),
            strokeDash=alt.StrokeDash(
                "tissue_label:N",
                scale=alt.Scale(domain=list(TISSUE_LABEL.values()), range=[[1, 0], [5, 5]]),
                legend=None,
            ),
            tooltip=["tissue_label", "stage", alt.Tooltip("mean_tpm:Q", format=".2f")],
        )
    )
    rec = card.get("recommended_stage")
    if isinstance(rec, str) and rec.startswith("S"):
        rule = (
            alt.Chart(pd.DataFrame({"x": [int(rec[1:])]}))
            .mark_rule(color="#d62728", strokeDash=[5, 5])
            .encode(x="x:Q")
        )
        chart = line + rule
    else:
        chart = line
    st.altair_chart(chart, width="stretch")

    with st.container(horizontal=True):
        st.metric("推荐转化窗口", str(rec), border=True)
        st.metric("胶乳峰值", f"{card.get('latex_peak_tpm')} TPM",
                  str(card.get("latex_peak_stage")), border=True)
        st.metric("胶乳上升倍数", f"×{card.get('latex_fold_peak_vs_first')}",
                  str(card.get("latex_first_stage")), border=True)
        st.metric("根爆发期", str(card.get("root_burst_stage")), border=True)
    st.caption(str(card.get("card_text")))
