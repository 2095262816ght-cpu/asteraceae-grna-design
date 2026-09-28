"""Streamlit demo（计B 9.25–9.26 · B4）。

启动（在 cs_pipeline/ 目录下）：
    streamlit run app/app.py

架构升级（2026-09-25 · /improve-codebase-architecture）：
- Tab 1 业务下沉至深度模块 `CandidateRankingEngine`（数据连接、版本回退、过滤与排序调度）；
- Tab 2 子进程与跨环境生命周期下沉至深度模块 `InferenceClient`（解释器探测、DLL 注入与降级状态解析）；
- 序列规格校验统一由 `core.sequence_spec.validate_seq30` 单点定义。
"""
import io
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
    from core.atac_annotator import (
        COL_IN_PEAK,
        COL_STATUS,
        STATUS_NEAR,
        DISPLAY_MAP as ATAC_DISPLAY_MAP,
        annotate_guides,
        detect_coord_columns,
        load_default_atac,
        peaks_from_dataframe,
    )
except ImportError:
    from cs_pipeline.core.sequence_spec import validate_seq30
    from cs_pipeline.core.atac_annotator import (
        COL_IN_PEAK,
        COL_STATUS,
        STATUS_NEAR,
        DISPLAY_MAP as ATAC_DISPLAY_MAP,
        annotate_guides,
        detect_coord_columns,
        load_default_atac,
        peaks_from_dataframe,
    )

try:
    from batch_importer import (
        compute_file_hash,
        detect_id_column,
        detect_sequence_column,
        export_dataframe_to_csv,
        export_dataframe_to_excel,
        generate_template_csv,
        generate_template_excel,
        get_excel_sheet_names,
        merge_batch_results,
        precheck_table,
        read_uploaded_table,
    )
except ImportError:
    from app.batch_importer import (
        compute_file_hash,
        detect_id_column,
        detect_sequence_column,
        export_dataframe_to_csv,
        export_dataframe_to_excel,
        generate_template_csv,
        generate_template_excel,
        get_excel_sheet_names,
        merge_batch_results,
        precheck_table,
        read_uploaded_table,
    )

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


@st.cache_resource(show_spinner="加载 ATAC-seq 染色质开放峰表…")
def get_default_atac_atlas():
    return load_default_atac(BASE)


# =====================================================================
# Tab 1：按基因名检索与推荐
# =====================================================================
with tab1:
    engine = get_ranking_engine()

    # 模型版本与效率分声明
    if engine.callout.kind == "success":
        st.success(engine.callout.message, icon="✅")
    elif engine.callout.kind == "warning":
        st.warning(engine.callout.message, icon="⚠️")
    else:
        st.info(engine.callout.message)

    if not engine.has_offtarget:
        st.info("脱靶计数尚未生成，脱靶相关列暂为空值。")

    if engine.has_atac:
        st.info(
            "已整合莴苣 ATAC-seq 染色质开放峰注释：候选表默认附「ATAC状态 / 峰ID / 距峰中心 / 峰强度FC / 可及性分」列；"
            "「排序依据」选「组织优先指数+ATAC加权」可启用表观可及性加权排序（默认排序不受影响）。"
        )

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
# Tab 2：按自定义序列打分与表格批量检测
# =====================================================================
with tab2:
    st.info(
        "已接入自主训练的 Stacking 集成模型预测引擎（融合 DeepSpCas9、CRISPRon 及序列物理特征）；"
        "支持输入 30bp 序列实时输出 DeepSpCas9 单模型分与 Stacking 集成预测分。"
    )

    score_mode = st.segmented_control(
        "检测输入模式",
        options=["手动粘贴输入", "从 Excel / CSV 表格批量导入"],
        default="手动粘贴输入",
    )
    if not score_mode:
        score_mode = "手动粘贴输入"

    # -----------------------------------------------------------------
    # 分支 A：手动粘贴序列
    # -----------------------------------------------------------------
    if score_mode == "手动粘贴输入":
        st.caption("提示：在下方序列框粘贴 30bp 序列（每行一条），需 Ctrl+Enter 生效后再点「打分」。")
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
                        st.session_state["manual_infer_res"] = res
                    except InferenceError as exc:
                        st.error(str(exc))
                    except Exception as exc:  # noqa: BLE001 兜底展示
                        st.error(f"打分过程出现未预期错误：{exc}")

        # 展示最近一次打分结果（保持跨 rerun 可持久化下载）
        if "manual_infer_res" in st.session_state:
            cached_res = st.session_state["manual_infer_res"]
            st.success(
                f"完成 {cached_res.total_count} 条序列打分，"
                f"耗时 {cached_res.latency_s:.1f} s"
            )
            if cached_res.has_approximated:
                st.warning(cached_res.warning_message, icon="⚠️")
            else:
                st.caption(cached_res.caption_message)

            st.dataframe(cached_res.display_df, width="stretch")
            m_dl1, m_dl2 = st.columns(2)
            with m_dl1:
                st.download_button(
                    "下载打分结果（CSV）",
                    data=cached_res.raw_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="crispr_stacking_scores.csv",
                    mime="text/csv",
                    key="dl_scores",
                )
            with m_dl2:
                st.download_button(
                    "下载打分结果（Excel）",
                    data=export_dataframe_to_excel(cached_res.display_df),
                    file_name="crispr_stacking_scores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_scores_excel",
                )

    # -----------------------------------------------------------------
    # 分支 B：从 Excel / CSV 表格批量导入检测
    # -----------------------------------------------------------------
    else:
        with st.container(border=True):
            st.markdown("#### 1. 规范说明与模板下载")
            st.caption(
                "适合实验室或高通量筛选场景：支持上传 `.xlsx`、`.xls`、`.csv` 文件批量打分。"
                "表格可包含自定义 ID、基因名、染色体位置等任意附加列，预测完成后将**完整保留原表所有列**并追加预测打分结果。"
            )
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.download_button(
                    "📥 下载 Excel 导入模板 (.xlsx)",
                    data=generate_template_excel(),
                    file_name="gRNA_batch_import_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_tpl_excel",
                )
            with t_col2:
                st.download_button(
                    "📥 下载 CSV 导入模板 (.csv)",
                    data=generate_template_csv(),
                    file_name="gRNA_batch_import_template.csv",
                    mime="text/csv",
                    key="dl_tpl_csv",
                )

        uploaded_file = st.file_uploader(
            "上传待检测表格文件（支持 .xlsx、.xls 或 .csv）",
            type=["xlsx", "xls", "csv"],
            key="batch_uploader",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            file_hash = compute_file_hash(file_bytes)
            sheet_names = get_excel_sheet_names(io.BytesIO(file_bytes), uploaded_file.name)

            if len(sheet_names) > 1:
                selected_sheet = st.selectbox(
                    "检测到多工作表，请选择待检测的工作表 (Sheet)",
                    sheet_names,
                    key="batch_sheet_selector",
                )
            else:
                selected_sheet = sheet_names[0]

            try:
                raw_df = read_uploaded_table(
                    io.BytesIO(file_bytes), uploaded_file.name, sheet_name=selected_sheet
                )
            except Exception as exc:
                st.error(f"解析上传文件失败：{exc}")
                raw_df = None

            if raw_df is not None:
                detected_seq = detect_sequence_column(raw_df)
                detected_id = detect_id_column(raw_df, seq_col=detected_seq)

                with st.container(border=True):
                    st.markdown("#### 2. 表格列配置与数据预览")
                    col_cfg1, col_cfg2 = st.columns(2)
                    with col_cfg1:
                        seq_idx = list(raw_df.columns).index(detected_seq) if detected_seq in raw_df.columns else 0
                        selected_seq_col = st.selectbox(
                            "选择 30bp 序列所在列",
                            options=list(raw_df.columns),
                            index=seq_idx,
                            help="系统已智能推荐最佳列，可手动调整",
                        )
                    with col_cfg2:
                        id_opts = ["（无，使用默认序号）"] + list(raw_df.columns)
                        id_idx = id_opts.index(detected_id) if detected_id and detected_id in id_opts else 0
                        selected_id_col = st.selectbox(
                            "选择靶点标识/ID列（可选）",
                            options=id_opts,
                            index=id_idx,
                            help="用于在质检与导出中标记各靶点编号",
                        )

                    with st.expander(f"查看当前工作表（{selected_sheet}）前 5 行预览（全表共 {len(raw_df)} 行数据）"):
                        preview_df = raw_df.drop(columns=["_excel_row_num"], errors="ignore")
                        st.dataframe(preview_df.head(5), width="stretch")

                # 执行序列质检与预检分析（绑定 ID 列）
                actual_id_col = selected_id_col if selected_id_col != "（无，使用默认序号）" else None
                precheck = precheck_table(raw_df, selected_seq_col, id_col=actual_id_col)

                with st.container(border=True):
                    st.markdown("#### 3. 序列规格即时质检")
                    q1, q2, q3 = st.columns(3)
                    q1.metric("表格数据总行数", precheck.total_rows)
                    q2.metric("合规有效序列数", precheck.valid_count)
                    q3.metric("格式异常行数", precheck.invalid_count)

                    if precheck.has_issues:
                        st.warning(
                            f"检测到 **{precheck.invalid_count}** 行序列不符合 30bp 基因组靶点规范（如长度不足 30bp、非 NGG PAM 或含非法碱基）。"
                            "批量打分时将**自动跳过**异常行，并在最终导出表中保留原行并标注异常诊断原因。"
                        )
                        with st.expander(f"查看 {precheck.invalid_count} 条格式异常明细"):
                            issue_rows = []
                            for issue in precheck.issues:
                                item = {"Excel行号": issue.row_number}
                                if actual_id_col:
                                    item["靶点ID"] = issue.id_value or "（未提供）"
                                item["原序列内容"] = issue.raw_value
                                item["异常原因"] = issue.error_message
                                issue_rows.append(item)
                            st.dataframe(pd.DataFrame(issue_rows), width="stretch")
                    else:
                        st.success(
                            f"质检全部通过！全表 {precheck.valid_count} 条序列均符合 30bp 规范（4nt 5'侧翼 + 20nt guide + NGG PAM + 3nt 3'侧翼）。",
                            icon="✅",
                        )

                # 独一无二防碰撞缓存 Key
                cache_key = f"{file_hash}_{selected_sheet}_{selected_seq_col}_{actual_id_col}"

                # 开始批量打分
                if precheck.valid_count == 0:
                    st.error("表格中未检测到任何合规的 30bp 序列，请核实序列列选择或查看模板规范。")
                else:
                    if st.button(
                        f"🚀 开始批量检测打分（共 {precheck.valid_count} 条有效序列）",
                        type="primary",
                        key="btn_run_batch_scoring",
                    ):
                        client = get_inference_client()
                        try:
                            # 动态超时：根据条数合理调整超时阈值
                            dynamic_timeout = max(180, len(precheck.valid_sequences) * 5 + 60)
                            with st.spinner(
                                f"正在调用双模型与集成模型对 {precheck.valid_count} 条序列执行批量打分，请稍候..."
                            ):
                                infer_res = client.score_sequences(
                                    precheck.valid_sequences,
                                    timeout_s=dynamic_timeout,
                                )
                                merged_df = merge_batch_results(raw_df, precheck, infer_res)
                                st.session_state["batch_infer_state"] = {
                                    "key": cache_key,
                                    "infer_res": infer_res,
                                    "merged_df": merged_df,
                                    "filename": uploaded_file.name,
                                }
                        except InferenceError as exc:
                            st.error(str(exc))
                        except Exception as exc:  # noqa: BLE001 兜底展示
                            st.error(f"批量打分过程出现未预期错误：{exc}")

                # 渲染批量打分结果展示与导出
                batch_cache = st.session_state.get("batch_infer_state")
                if batch_cache and batch_cache.get("key") == cache_key:
                    infer_res = batch_cache["infer_res"]
                    merged_df = batch_cache["merged_df"]

                    st.markdown("---")
                    st.subheader("批量打分检测结果总表")
                    st.success(
                        f"批量打分完成！共计算 {infer_res.total_count} 条有效序列，"
                        f"耗时 {infer_res.latency_s:.1f} 秒。"
                    )
                    if infer_res.has_approximated:
                        st.warning(infer_res.warning_message, icon="⚠️")
                    else:
                        st.caption(infer_res.caption_message)

                    st.dataframe(merged_df, width="stretch")

                    # 双格式导出
                    stem_name = Path(batch_cache["filename"]).stem
                    b_dl1, b_dl2 = st.columns(2)
                    with b_dl1:
                        st.download_button(
                            "📥 导出完整检测结果为 Excel (.xlsx)",
                            data=export_dataframe_to_excel(merged_df),
                            file_name=f"{stem_name}_crispr_predictions.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_batch_excel",
                        )
                    with b_dl2:
                        st.download_button(
                            "📥 导出完整检测结果为 CSV (.csv)",
                            data=export_dataframe_to_csv(merged_df),
                            file_name=f"{stem_name}_crispr_predictions.csv",
                            mime="text/csv",
                            key="dl_batch_csv",
                        )

                    # -------------------------------------------------------------
                    # 表观注释：ATAC-seq 染色质开放峰（可选注释层，与打分解耦）
                    # -------------------------------------------------------------
                    st.markdown("---")
                    st.markdown("#### 表观注释：ATAC-seq 染色质开放峰（可选）")
                    st.caption(
                        "按坐标区间为每条靶点匹配染色质开放峰，追加「ATAC状态 / 峰ID / 距峰中心 / 峰强度FC / 可及性分」列。"
                        "可及性分口径：峰内 0.6+0.4×min(1, FC/10)，峰缘 5kb 内线性衰减至 0，其余为 0。"
                    )
                    chrom_c, start_c, end_c = detect_coord_columns(merged_df)
                    if not (chrom_c and start_c and end_c):
                        st.info(
                            "当前表格未探测到染色体与起止坐标列（如 Chr / Start / End），无法进行 ATAC 区间匹配。"
                            "在原表补充坐标列后重新上传即可启用表观注释。"
                        )
                    else:
                        atac_mode = st.segmented_control(
                            "ATAC 峰表来源",
                            options=["不注释", "内置莴苣 ATAC 峰表", "上传自定义 ATAC peaks 表"],
                            default="不注释",
                            key="batch_atac_mode",
                        )
                        if not atac_mode:
                            atac_mode = "不注释"

                        atlas = None
                        if atac_mode == "内置莴苣 ATAC 峰表":
                            atlas = get_default_atac_atlas()
                            if atlas is None:
                                st.warning(
                                    "未找到内置莴苣 ATAC 峰表"
                                    "（data/reference_genomes/1-3_Stem_lettuce_ATAC_peaks.xlsx），请改用自定义上传。",
                                    icon="⚠️",
                                )
                        elif atac_mode == "上传自定义 ATAC peaks 表":
                            peaks_file = st.file_uploader(
                                "上传 ATAC peaks 表（需含 Chr / Start / End 列，兼容 LettuceGDB 口径与常见 BED/narrowPeak 导出）",
                                type=["xlsx", "xls", "csv"],
                                key="batch_atac_uploader",
                            )
                            if peaks_file is not None:
                                try:
                                    pk_bytes = peaks_file.getvalue()
                                    if peaks_file.name.lower().endswith((".xlsx", ".xls")):
                                        raw_peaks = pd.read_excel(io.BytesIO(pk_bytes))
                                    else:
                                        raw_peaks = pd.read_csv(io.BytesIO(pk_bytes))
                                    atlas = peaks_from_dataframe(raw_peaks)
                                except Exception as exc:  # noqa: BLE001 兜底展示
                                    st.error(f"解析 ATAC 峰表失败：{exc}")

                        if atlas is not None:
                            annotated = annotate_guides(
                                merged_df, atlas, chrom_col=chrom_c, start_col=start_c, end_col=end_c
                            )
                            display_df = annotated.rename(columns=ATAC_DISPLAY_MAP)
                            display_df[ATAC_DISPLAY_MAP[COL_IN_PEAK]] = display_df[ATAC_DISPLAY_MAP[COL_IN_PEAK]].map(
                                {True: "是", False: "否"}
                            )

                            m1, m2, m3 = st.columns(3)
                            m1.metric("落入 ATAC 开放峰（条）", int(annotated[COL_IN_PEAK].sum()))
                            m2.metric("峰近端 ≤5kb（条）", int((annotated[COL_STATUS] == STATUS_NEAR).sum()))
                            m3.metric("ATAC 峰表峰数", atlas.n_peaks)

                            st.dataframe(display_df, width="stretch")

                            a_dl1, a_dl2 = st.columns(2)
                            with a_dl1:
                                st.download_button(
                                    "📥 导出含 ATAC 注释结果为 Excel (.xlsx)",
                                    data=export_dataframe_to_excel(display_df),
                                    file_name=f"{stem_name}_crispr_predictions_atac.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="dl_batch_atac_excel",
                                )
                            with a_dl2:
                                st.download_button(
                                    "📥 导出含 ATAC 注释结果为 CSV (.csv)",
                                    data=export_dataframe_to_csv(display_df),
                                    file_name=f"{stem_name}_crispr_predictions_atac.csv",
                                    mime="text/csv",
                                    key="dl_batch_atac_csv",
                                )

