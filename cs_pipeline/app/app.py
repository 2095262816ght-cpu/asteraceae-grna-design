"""Streamlit demo（计B 9.25–9.26 · B4）。

启动（在 cs_pipeline/ 目录下）：
    streamlit run app/app.py

两个 tab：
1. 按基因名检索：49 个 NLR 代表基因的候选 gRNA 浏览/过滤/下载。
2. 按自定义序列打分：30bp 序列经子进程调用独立 conda 环境中的
   genet DeepSpCas9 模型实时打分（app/score_deepspcas9_cli.py）。

效率分现状（2026-09-17 定位声明）：
- 本工具定位为【排序推荐】：效率分用于同一基因内候选 guide 的相对排序（取 top 3–5 送实验），
  非绝对 indel% 承诺；模型 LOGO-CV ρ=0.414（未达 0.5，如实标注）。
- Tab1 展示 efficiency_score_full_0916（全量重训模型 + 真实双模型打分，9.16 版）。
- Tab2 提供 DeepSpCas9 单模型分及 Stacking 集成模型分实时打分。
"""
import io
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent  # cs_pipeline/

# 独立打分环境的 python（含 genet + DeepSpCas9 权重）。
CRISPR_PYTHON = os.environ.get("CRISPR_PYTHON")
if not CRISPR_PYTHON:
    # 优先推断：若当前运行在 grna-demo 等 conda 环境中，直接寻找同目录下的 crispr 环境
    sibling_crispr = Path(sys.executable).parent.parent / "envs" / "crispr" / "python.exe"
    same_dir_crispr = Path(sys.executable).parent.parent / "crispr" / "python.exe"
    candidates = [
        str(sibling_crispr),
        str(same_dir_crispr),
        r"D:\Miniconda\envs\crispr\python.exe",
        str(Path.home() / "miniconda3" / "envs" / "crispr" / "python.exe"),
        str(Path.home() / "anaconda3" / "envs" / "crispr" / "python.exe"),
        r"C:\miniconda3\envs\crispr\python.exe",
        r"C:\anaconda3\envs\crispr\python.exe",
        r"C:\ProgramData\miniconda3\envs\crispr\python.exe",
        r"C:\ProgramData\anaconda3\envs\crispr\python.exe",
        str(Path(os.environ.get("CONDA_PREFIX_1", Path.home() / "anaconda3"))
            / "envs" / "crispr" / "python.exe"),
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            CRISPR_PYTHON = str(candidate)
            break
if not CRISPR_PYTHON:
    CRISPR_PYTHON = "python"

CLI_SCRIPT = Path(__file__).resolve().parent / "score_deepspcas9_cli.py"
SCORE_TIMEOUT_S = 120

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


# =====================================================================
# Tab 1：按基因名检索
# =====================================================================
@st.cache_data
def load_data():
    data = pd.read_csv(BASE / "demo/app_data.csv")
    genes = pd.read_csv(BASE / "demo/app_genes.csv")
    return data, genes


with tab1:
    data, genes = load_data()
    has_offtarget = data["offtarget_count_mis3"].notna().any()
    # 优先使用 2026-09-21 v2.1 终版分层模型重打分列（真实 DeepSpCas9+CRISPRon + noB879 纯A级金标准训练，
    # 核心靶点泛化上限 ρ=0.464，留出测试集 ρ=0.342）；旧列仅作留档
    has_v21 = "efficiency_score_v21_nob879" in data.columns and data["efficiency_score_v21_nob879"].notna().any()
    has_full = "efficiency_score_full_0916" in data.columns and data["efficiency_score_full_0916"].notna().any()
    has_stacking = has_v21 or has_full or ("efficiency_score" in data.columns and data["efficiency_score"].notna().any())

    if has_v21:
        st.success(
            "本页“效率分（v2.1排序参考）”用于**候选 guide 的相对排序与择优**（融合真实 DeepSpCas9、CRISPRon 及序列物理特征；2026-09-21 终版形态二分层模型，基于 noB879 纯 A 级金标准训练）。建议同一基因内取 top 3–5 条送实验终筛；分数为排序参考，非绝对突变率承诺（低混杂核心靶点上限 ρ=0.464，留出测试集 ρ=0.342）。",
            icon="✅",
        )
    elif has_full:
        st.success(
            "本页“效率分（Stacking预测）”用于**候选 guide 的相对排序**（融合 DeepSpCas9、CRISPRon 及序列物理特征；2026-09-16 全量数据重训版）。建议同一基因内取 top 3–5 条送实验终筛；分数为排序参考，非绝对效率承诺（模型 LOGO-CV ρ=0.414）。",
            icon="✅",
        )
    elif has_stacking:
        st.success(
            "本页“效率分（Stacking预测）”为自主训练的 Stacking 集成模型预测分数（融合 DeepSpCas9、CRISPRon 及序列物理特征，反映 Hi-TOM 实测突变效率）。",
            icon="✅",
        )
    else:
        st.warning(
            "本页“效率分（占位）”列为序列启发式占位分（GC/Tm），**非模型预测**，"
            "待计A Stacking 模型接入后替换为真实预测分并重排序。",
            icon="⚠️",
        )
    if not has_offtarget:
        st.info("脱靶计数尚未生成，脱靶相关列暂为空值。")

    gene_id = st.selectbox(
        "选择基因（可输入关键字过滤）", sorted(genes.gene_id.unique())
    )

    t0 = time.perf_counter()
    ginfo = genes[genes.gene_id == gene_id].iloc[0]
    cand = data[data.gene_id == gene_id].copy()

    if has_v21:
        eff_col = "efficiency_score_v21_nob879"
        eff_label = "效率分（v2.1排序参考）"
    elif has_full:
        eff_col = "efficiency_score_full_0916"
        eff_label = "效率分（Stacking排序参考）"
    elif has_stacking:
        eff_col = "efficiency_score"
        eff_label = "效率分（Stacking排序参考）"
    else:
        eff_col = "efficiency_placeholder"
        eff_label = "效率分（占位）"

    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        hide_cen = st.checkbox("过滤着丝粒区 guide", value=True)
    with colf2:
        region = st.multiselect(
            "区域类型", ["promoter", "exon"], default=["promoter", "exon"]
        )
    with colf3:
        sort_key = st.selectbox(
            "排序依据",
            [
                f"{eff_label} 降序（推荐）",
                "脱靶计数 mis3 升序" if has_offtarget else "脱靶计数 mis3 升序（待数据）",
                "GC% 接近 50%",
            ],
        )

    if hide_cen:
        cand = cand[~cand.in_centromere]
    cand = cand[cand.region_type.isin(region)]

    if sort_key.startswith(eff_label):
        cand = cand.sort_values(eff_col, ascending=False)
    elif sort_key.startswith("脱靶"):
        cand = cand.sort_values(
            "offtarget_count_mis3", ascending=True, na_position="last"
        )
    else:
        cand = cand.assign(gc_dist=(cand.gc_pct - 50).abs()).sort_values("gc_dist")

    elapsed = time.perf_counter() - t0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("染色体", str(ginfo.g_chrom))
    c2.metric("基因坐标", f"{int(ginfo.g_start):,}–{int(ginfo.g_end):,}")
    c3.metric("链", str(ginfo.g_strand))
    c4.metric("NLR 类型", str(ginfo.get("nlr_type", "—")))
    c5.metric("候选数（过滤后）", len(cand))

    cand = cand.rename(
        columns={
            eff_col: eff_label,
            "offtarget_count_mis1": "脱靶 mis1",
            "offtarget_count_mis2": "脱靶 mis2",
            "offtarget_count_mis3": "脱靶 mis3",
            "exact_match_count": "完全匹配数",
            "in_centromere": "着丝粒区",
        }
    )
    show_cols = [
        "guide_id", "seq20", "pam", "chrom", "start", "end", "strand",
        "region_type", "gc_pct", "tm_c", eff_label,
        "脱靶 mis1", "脱靶 mis2", "脱靶 mis3", "完全匹配数", "着丝粒区",
    ]
    show_cols = [c for c in show_cols if c in cand.columns]
    view = cand[show_cols]

    st.subheader("推荐 Top 10")
    st.dataframe(view.head(10), width="stretch")

    with st.expander(f"查看全部 {len(view)} 条候选"):
        st.dataframe(view, width="stretch")

    st.download_button(
        "下载当前过滤结果（CSV）",
        data=view.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"grna_candidates_{gene_id}.csv",
        mime="text/csv",
    )
    st.caption(f"查询耗时 {elapsed * 1000:.0f} ms（要求 <5 s）")


# =====================================================================
# Tab 2：按自定义序列打分
# =====================================================================
SEQ_RE = re.compile(r"^[ACGT]{30}$")


def validate_seq30(seq: str) -> str | None:
    """返回错误信息；合法则返回 None。布局：4nt 上游+20nt guide+NGG+3nt 下游。"""
    if len(seq) != 30:
        return f"长度为 {len(seq)}，须为 30bp"
    if not SEQ_RE.match(seq):
        return "含非法字符，仅允许 A/C/G/T"
    if seq[25:27] != "GG":
        return "第 25–27 位须为 NGG PAM（即第 26、27 位为 GG）"
    return None


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
                try:
                    t1 = time.perf_counter()
                    env = os.environ.copy()
                    py_dir = Path(CRISPR_PYTHON).parent
                    lib_bin = py_dir / "Library" / "bin"
                    if lib_bin.exists():
                        env["PATH"] = f"{lib_bin};{py_dir};{env.get('PATH', '')}"

                    proc = subprocess.run(
                        [CRISPR_PYTHON, str(CLI_SCRIPT)],
                        input="\n".join(good) + "\n",
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=SCORE_TIMEOUT_S,
                    )
                    if proc.returncode != 0:
                        st.error("打分子进程失败，stderr 摘录：")
                        st.code(proc.stderr[-2000:] or "（无输出）")
                    else:
                        scores = pd.read_csv(io.StringIO(proc.stdout))
                        display_df = scores.rename(
                            columns={
                                "seq30": "30bp 序列",
                                "deepspcas9_score": "DeepSpCas9 分数",
                                "stacking_score": "Stacking 集成效率分",
                            }
                        )
                        st.success(
                            f"完成 {len(scores)} 条序列打分，"
                            f"耗时 {time.perf_counter() - t1:.1f} s"
                        )
                        st.dataframe(display_df, width="stretch")
                        st.download_button(
                            "下载打分结果（CSV）",
                            data=scores.to_csv(index=False).encode("utf-8-sig"),
                            file_name="crispr_stacking_scores.csv",
                            mime="text/csv",
                            key="dl_scores",
                        )
                except subprocess.TimeoutExpired:
                    st.error(f"打分超时（>{SCORE_TIMEOUT_S} s），请减少序列条数后重试。")
                except FileNotFoundError:
                    st.error("找不到打分环境的 Python 解释器，请检查 demo 运行环境配置。")
                except Exception as exc:  # noqa: BLE001 兜底展示
                    st.error(f"打分过程出现未预期错误：{exc}")
