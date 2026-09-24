# -*- coding: utf-8 -*-
"""多组织表达看板组件（方案1）。

供 app/app.py Tab 1 调用：demo 基因（LsaT2T* 命名空间）经 scripts/16 产出的
crosswalk 映射到莴苣 v1.1c 的 LSA 基因，展示 5 组织表达丰度、组织特异性指数与
靶向适宜性诊断。

不可映射基因（crosswalk tier4，弱票作废）如实标注原因，**不编造表达值**。
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
EXPR_CSV = BASE / "data" / "expression" / "1-3_lettuce_5tissue_expression_matrix.csv"
XWALK_CSV = BASE / "results" / "crosswalk_lsa_t2t_0923.csv"

TISSUES = {"Root": "根", "Stem": "茎", "Leaf": "叶", "Flower": "花", "Seed": "种子"}
TISSUE_ORDER = list(TISSUES)
LOW_TPM = 0.5
HIGH_TPM = 10.0


@st.cache_data(show_spinner="加载莴苣 5 组织表达矩阵…")
def _load_expression() -> pd.DataFrame:
    return pd.read_csv(EXPR_CSV).set_index("GeneID")


@st.cache_data(show_spinner="加载 LSA↔T2T crosswalk…")
def _load_crosswalk() -> pd.DataFrame:
    return pd.read_csv(XWALK_CSV).set_index("gene_id")


def _lookup(gene_id: str):
    """返回 (crosswalk 行, LSA, 错误说明)；错误说明非 None 时不可展示表达。"""
    xw = _load_crosswalk()
    if gene_id not in xw.index:
        return None, None, "该基因不在 crosswalk 表（results/crosswalk_lsa_t2t_0923.csv）中。"
    row = xw.loc[gene_id]
    lsa = row["lsa_primary"]
    if pd.isna(lsa):
        return row, None, (
            f"该基因座在莴苣 v1.1c 表达矩阵中**无对应注释**（crosswalk tier {int(row['tier'])}，"
            f"guide 解析占比 {row['lsa_resolved_frac']:.1%}）：序列在 v1.1c 中缺失/高度分歧，"
            f"或序列共线但存在注释缺口。详见 results/crosswalk_lsa_t2t_report_0923.md，"
            f"故不展示表达值。"
        )
    expr = _load_expression()
    if lsa not in expr.index:
        return row, None, f"crosswalk 主映射 {lsa} 不在表达矩阵中，属数据不一致，请报告。"
    return row, lsa, None


def _tau(tpm: pd.Series) -> float:
    mx = float(tpm.max())
    if mx <= 0:
        return float("nan")
    return float((1.0 - tpm / mx).sum() / (len(tpm) - 1))


def render_gene_expression(gene_id: str, target: str = "Leaf") -> None:
    """在 Tab 1 中渲染指定 demo 基因的多组织表达看板与表型诊断。

    target 由 app.py 的目标组织控件传入（方案3 重排与诊断共用同一选择）。
    """
    with st.container(border=True):
        st.markdown(":material/biotech: **多组织表达看板**（莴苣 v1.1c · 根/茎/叶/花/种子）")
        row, lsa, err = _lookup(gene_id)
        if err is not None:
            st.warning(err, icon=":material/warning:")
            return

        tpm = _load_expression().loc[lsa, TISSUE_ORDER].astype(float)
        tau = _tau(tpm)
        top_tissue = TISSUES[tpm.idxmax()]

        with st.container(horizontal=True):
            st.metric("v1.1c 映射", lsa, border=True,
                      help=f"crosswalk tier {int(row['tier'])}，投票占比 {row['lsa_vote_frac']:.0%}")
            st.metric("最高表达组织", f"{top_tissue}（{tpm.max():.1f} TPM）", border=True)
            st.metric("组织特异性 τ", f"{tau:.2f}", border=True,
                      help="τ→1 极度组织特异；τ→0 管家基因泛表达")

        chart_df = pd.DataFrame({
            "组织": [TISSUES[t] for t in TISSUE_ORDER],
            "TPM": [float(tpm[t]) for t in TISSUE_ORDER],
        })
        chart = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X("TPM:Q", title="TPM"),
                y=alt.Y("组织:N", sort=[TISSUES[t] for t in TISSUE_ORDER], title=None),
                color=alt.Color("TPM:Q", scale=alt.Scale(scheme="greenblue"), legend=None),
                tooltip=["组织", alt.Tooltip("TPM:Q", format=".2f")],
            )
        )
        st.altair_chart(chart, width="stretch")

        val = float(tpm[target])
        if val < LOW_TPM:
            st.warning(
                f"⚠️ 弱表型警示：该基因在所选组织（{TISSUES[target]}）中转录静默"
                f"（TPM {val:.2f} < {LOW_TPM}），CRISPR 敲除可能无法诱导明显生物学表型。"
            )
        elif val >= HIGH_TPM:
            st.success(
                f"✅ 适宜靶向：该基因在所选组织（{TISSUES[target]}）中高度转录"
                f"（TPM {val:.1f} ≥ {HIGH_TPM}），染色质处于开放状态，预期编辑响应好。"
            )
        else:
            st.info(
                f"中等表达：所选组织（{TISSUES[target]}）TPM {val:.2f}，"
                f"介于 {LOW_TPM} 与 {HIGH_TPM} 之间；表型预期中等，建议结合蛋白水平验证。"
            )

        notes = []
        if int(row["n_cluster"]) > 1:
            notes.append(
                f"该基因座为 NLR 串联重复簇：主映射 {lsa}（投票 {row['lsa_vote_frac']:.0%}），"
                f"簇成员 {row['lsa_cluster']}；看板展示主映射基因的表达，簇内旁系可能不同。"
            )
        if pd.notna(row["scaffold_evidence"]):
            notes.append(
                f"映射证据来自未挂载 scaffold（{row['scaffold_evidence']}）："
                f"该基因座在 v1.1c 中未挂载到染色体上。"
            )
        if notes:
            st.caption(" ".join(notes))
