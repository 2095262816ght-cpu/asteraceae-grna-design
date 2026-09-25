"""Streamlit demo（计B 9.25–9.26 · B4）。

启动（在 cs_pipeline/ 目录下）：
    streamlit run app/app.py

架构升级（2026-09-25 · /improve-codebase-architecture）：
- Tab 1 业务下沉至深度模块 `CandidateRankingEngine`（数据连接、版本回退、过滤与排序调度）；
- Tab 2 子进程与跨环境生命周期下沉至深度模块 `InferenceClient`（解释器探测、DLL 注入与降级状态解析）；
- 序列规格校验统一由 `core.sequence_spec.validate_seq30` 单点定义。
"""
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent  # cs_pipeline/
APP_DIR = Path(__file__).resolve().parent
for p in (str(BASE), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from inference_client import InferenceClient, InferenceError
    from recommendation_engine import CandidateRankingEngine
except ImportError:
    from app.inference_client import InferenceClient, InferenceError
    from app.recommendation_engine import CandidateRankingEngine

try:
    from core.sequence_spec import validate_seq30
except ImportError:
    from cs_pipeline.core.sequence_spec import validate_seq30
import expression_visualizer
import tks_window_visualizer

st.set_page_config(
    page_title="莴苣基因编辑 gRNA 设计与脱靶评估工具（v2.1）",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("莴苣基因编辑 gRNA 设计与脱靶评估工具（v2.1）")
st.caption(
    "模型路线：DeepSpCas9 + CRISPRon 双模型打分 → 分层选择性 Beta-Binomial GLMM 排序集成（v2.1 / noB879 纯A级金标准训练）"
    " → 基因组候选扫描 → 脱靶过滤 · 当前 demo 范围：49 个 NLR 代表基因"
)

tab1, tab2 = st.tabs(["候选 gRNA 检索与推荐", "单序列实时打分"])


@st.cache_resource(show_spinner="加载推荐决策引擎与多组学资产…")
def get_ranking_engine() -> CandidateRankingEngine:
    return CandidateRankingEngine.load_from_directory(BASE)


@st.cache_resource
def get_inference_client() -> InferenceClient:
    return InferenceClient()


# =====================================================================
# Tab 1：按基因名检索与推荐
# =====================================================================
with tab1:
    engine = get_ranking_engine()

    # 模型版本与效率分声明
    if engine._callout.kind == "success":
        st.success(engine._callout.message, icon="✅")
    elif engine._callout.kind == "warning":
        st.warning(engine._callout.message, icon="⚠️")
    else:
        st.info(engine._callout.message)

    if not engine._has_offtarget:
        st.info("脱靶计数尚未生成，脱靶相关列暂为空值。")

    gene_id = st.selectbox(
        "选择基因（可输入关键字过滤）", engine.genes
    )
    target_tissue = st.segmented_control(
        "目标组织（方案3 重排与表达诊断跟随此选择）",
        options=expression_visualizer.TISSUE_ORDER,
        format_func=lambda k: expression_visualizer.TISSUES[k],
        default="Leaf",
    )

    t0 = time.perf_counter()

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        hide_cen = st.checkbox("过滤着丝粒区 guide", value=True)
    with colf2:
        region = st.multiselect(
            "区域类型", ["promoter", "exon"], default=["promoter", "exon"]
        )
    with colf3:
        sort_opts = engine.get_sort_options(target_tissue)
        sort_key = st.selectbox("排序依据", sort_opts)

    # 委托深度推荐引擎执行过滤、排序与多组学标注
    result = engine.rank(
        gene_id=gene_id,
        target_tissue=target_tissue,
        sort_key=sort_key,
        region_types=region,
        hide_centromere=hide_cen,
    )
    elapsed = time.perf_counter() - t0

    # 基因元数据摘要展示
    ginfo = result.gene_summary
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("染色体", ginfo.chrom)
    c2.metric("基因坐标", ginfo.coords_text)
    c3.metric("链", ginfo.strand)
    c4.metric("NLR 类型", ginfo.nlr_type)
    c5.metric("候选数（过滤后）", ginfo.total_candidates)

    # 组织表达图谱与靶向适宜性诊断
    expression_visualizer.render_gene_expression(gene_id, target_tissue)

    st.subheader("推荐 Top 10")
    st.dataframe(result.top10_df, width="stretch")

    with st.expander(f"查看全部 {len(result.all_df)} 条候选"):
        st.dataframe(result.all_df, width="stretch")

    st.download_button(
        "下载当前过滤结果（CSV）",
        data=result.all_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"grna_candidates_{gene_id}.csv",
        mime="text/csv",
    )
    st.caption(f"查询耗时 {elapsed * 1000:.0f} ms（要求 <5 s）")

    with st.expander("橡胶草（TKS）产胶时相决策（方案6）"):
        tks_window_visualizer.render_tks_window()


# =====================================================================
# Tab 2：按自定义序列打分
# =====================================================================
with tab2:
    st.info(
        "已接入自主训练的 Stacking 集成模型预测引擎（融合 DeepSpCas9、CRISPRon 及序列物理特征）；"
        "支持输入 30bp 序列实时输出 DeepSpCas9 单模型分与 Stacking 集成预测分。\n\n"
        "提示：序列框需 Ctrl+Enter 生效后再点「打分」。"
    )
    seq_input = st.text_area(
        "粘贴 30bp 序列（4nt 上游 + 20nt guide + NGG PAM + 3nt 下游），每行一条",
        height=150,
        placeholder="ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
    )

    if st.button("打分", type="primary"):
        seqs = [s.strip().upper() for s in seq_input.splitlines() if s.strip()]
        if not seqs:
            st.warning("请先输入至少一条序列。")
        else:
            errors = {s: validate_seq30(s) for s in seqs}
            bad = {s: e for s, e in errors.items() if e}
            good = [s for s in seqs if not errors[s]]

            for s, e in bad.items():
                st.error(f"序列无效：{s} —— {e}")

            if good:
                client = get_inference_client()
                try:
                    res = client.score_sequences(good)
                    st.success(
                        f"完成 {res.total_count} 条序列打分，"
                        f"耗时 {res.latency_s:.1f} s"
                    )
                    if res.has_approximated:
                        st.warning(res.warning_message, icon="⚠️")
                    else:
                        st.caption(res.caption_message)

                    st.dataframe(res.display_df, width="stretch")
                    st.download_button(
                        "下载打分结果（CSV）",
                        data=res.raw_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name="crispr_stacking_scores.csv",
                        mime="text/csv",
                        key="dl_scores",
                    )
                except InferenceError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 兜底展示
                    st.error(f"打分过程出现未预期错误：{exc}")
