"""Streamlit demo（计B 9.25–9.26），骨架见《分工详案_计算机系.md》B4 节。

启动：cd app && streamlit run app.py
"""
import sys

import pandas as pd
import streamlit as st

sys.path.append("..")
from scripts.predict import predict_efficiency  # 计A 9.17 交付的接口

st.set_page_config(page_title="菊科菊苣族 gRNA 设计工具", layout="wide")
st.title("菊科（菊苣族）CRISPR/Cas9 gRNA 设计工具")
st.caption("DeepSpCas9 + CRISPRon Stacking 集成模型 · 莴苣 T2T 基因组演示")

tab1, tab2 = st.tabs(["按基因名检索", "按自定义序列打分"])

with tab1:
    gene = st.text_input("输入基因 ID（如 lettuce_v2_00041910）")
    if gene:
        # TODO(9.25): 读 results/grna_candidates_lettuce_0923.csv、
        # offtarget_counts_0924.csv、centromere_regions.bed，合并效率分/脱靶数/着丝粒标注
        st.info("候选表与脱靶数据接入待 9.25 实现")

with tab2:
    seq = st.text_area("粘贴 30bp 序列（4nt上游+20nt guide+NGG+3nt下游），每行一条")
    if st.button("打分") and seq:
        seqs = [s.strip().upper() for s in seq.splitlines() if s.strip()]
        scores = predict_efficiency(seqs)
        st.dataframe(pd.DataFrame({"seq30": seqs, "efficiency_score": scores}))
