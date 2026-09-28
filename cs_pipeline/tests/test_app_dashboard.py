"""Demo 前端接线无头验证（Tab1 方案 1/3/5/6 + Tab2 CRISPRon 来源标注）。

在 cs_pipeline/ 下运行（grna-demo 环境）：
    python tests/test_app_dashboard.py

`test_app_dashboard`（约 5 秒，无外部依赖）覆盖 Tab1 九条路径：默认基因与默认排序、
方案3 优先指数列、方案5 危害列与面板内位点数、排序切换真实改变推荐、组织切换驱动诊断
与列名、高表达→适宜靶向、低表达→弱表型警示、unmappable→表达证据缺失、串联簇脚注、
方案6 时相组件与 S4 推荐窗口。

`test_tab2_crispron_source`（约 30 秒，需 crispr 环境；WSL 可选）验证 P0 修复：Tab2 必须
把 CRISPRon 特征的来源（WSL 实跑 / 近似式降级）如实透出，降级时须告警。

地面真值取自 results/crosswalk_lsa_t2t_0923.csv × data/expression/1-3_lettuce_5tissue_expression_matrix.csv。
"""
import io
import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

APP = Path(__file__).resolve().parents[1] / "app" / "app.py"

GENE_CLUSTER = "LsaT2T01G023690"      # → LSA25643，n_cluster=2，Leaf 中等表达
GENE_HIGH = "LsaT2T06G019420"         # → LSA15294，Leaf 98.2 TPM ⇒ 适宜靶向
GENE_LOW = "LsaT2T02G000110"          # → LSA31836，Leaf 0.0 TPM ⇒ 弱表型警示
GENE_UNMAPPABLE = "LsaT2T01G030600"   # tier4 弱票作废，无 LSA 主映射
TKS_FAMILIES = {"REF（TKS 成员 2 个）", "SRPP（TKS 成员 8 个）", "CPT（TKS 成员 4 个）"}

# demo Tab2 输入框预填的 placeholder 序列；其 CRISPRon 真实值 59.61、近似式 68.27（偏 14.5%），
# 是 P0「推理期特征伪造」的原始证据序列。
PROBE_SEQ30 = "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"
# 须与 app/app.py Tab2 的 src_labels 一致
SRC_LABELS = {"wsl_real": "真实模型实跑（WSL/容器原生）", "approximated": "⚠️ 近似式降级"}


def test_app_dashboard():
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, at.exception

    # 1. 默认态：首个基因 / Leaf / 方案3 优先指数为默认排序
    assert at.selectbox[0].value == GENE_CLUSTER, at.selectbox[0].value
    assert at.segmented_control[0].value == "Leaf"
    assert at.selectbox[1].value.startswith("组织优先指数"), at.selectbox[1].value
    print("[1] 默认基因 %s | 默认组织 Leaf | 默认排序 %s"
          % (at.selectbox[0].value, at.selectbox[1].value))

    # 2. 方案3 优先指数列 + 表达证据列；方案5 危害列 + 面板内位点数
    top = at.dataframe[0].value
    assert len(top) > 0, "默认基因的 Top10 表为空，后续断言会空洞通过"
    for frag in ("组织优先指数", "表达证据", "功能性脱靶危害", "面板内位点数"):
        assert any(frag in c for c in top.columns), f"缺少 {frag} 列；现有 {list(top.columns)}"
    print("[2] 四列齐备 | top3 %s | 表达证据 %s"
          % (top["guide_id"].head(3).tolist(), top["表达证据"].head(3).tolist()))

    # 3. 排序切换到纯效率分：推荐集合必须真的变
    eff_opt = next(o for o in at.selectbox[1].options if o.startswith("效率分"))
    at.selectbox[1].set_value(eff_opt).run()
    assert not at.exception, at.exception
    top_eff = at.dataframe[0].value["guide_id"].head(3).tolist()
    assert top_eff != top["guide_id"].head(3).tolist(), "重排未改变 top3，方案3 接线失效"
    print("[3] 排序切换 %s → top3 %s（顺序已变）" % (eff_opt, top_eff))

    # 4. 组织切换 Leaf→Root：诊断文案与危害列名跟随
    at.segmented_control[0].set_value("Root").run()
    assert not at.exception, at.exception
    assert any("功能性脱靶危害（根）" in c for c in at.dataframe[0].value.columns)
    root_diag = [x.value for x in list(at.success) + list(at.info) + list(at.warning)
                 if "所选组织（根）" in x.value]
    assert root_diag, "组织切换后诊断未跟随"
    print("[4] 根诊断：%s" % root_diag[0][:52])
    print("    注：切换组织后排序控件回到默认项 = %s（选项标签变化导致控件状态重置）"
          % at.selectbox[1].value)

    # 5. 高表达 → 适宜靶向（success 分支）
    at.segmented_control[0].set_value("Leaf").run()
    at.selectbox[0].set_value(GENE_HIGH).run()
    assert not at.exception, at.exception
    assert any("适宜靶向" in x.value for x in at.success), \
        [x.value[:40] for x in at.success]
    print("[5] %s → 适宜靶向分支命中" % GENE_HIGH)

    # 6. 低表达 → 弱表型警示（warning 分支）
    at.selectbox[0].set_value(GENE_LOW).run()
    assert not at.exception, at.exception
    assert any("弱表型警示" in x.value for x in at.warning), \
        [x.value[:40] for x in at.warning]
    print("[6] %s → 弱表型警示分支命中" % GENE_LOW)

    # 7. unmappable → 无对应注释 warning + 全表“表达证据缺失”，不编造表达值
    at.selectbox[0].set_value(GENE_UNMAPPABLE).run()
    assert not at.exception, at.exception
    assert any("无对应注释" in x.value for x in at.warning), "缺少不可映射 warning"
    evidence = at.dataframe[0].value["表达证据"]
    assert len(evidence) > 0, "不可映射基因的 Top10 表为空，断言会空洞通过"
    assert (evidence == "表达证据缺失").all(), evidence.unique()
    print("[7] %s → warning + 表达证据缺失（%d 行）" % (GENE_UNMAPPABLE, len(evidence)))

    # 8. 串联簇脚注
    at.selectbox[0].set_value(GENE_CLUSTER).run()
    assert not at.exception, at.exception
    assert any("串联重复簇" in x.value for x in at.caption), "缺少簇 caption"
    print("[8] %s → 串联簇脚注命中" % GENE_CLUSTER)

    # 9. 方案6 时相组件：三家族成员数 + 统一推荐 S4
    assert set(at.selectbox[2].options) == TKS_FAMILIES, at.selectbox[2].options
    for fam in ("CPT", "REF", "SRPP"):
        at.selectbox[2].set_value(fam).run()
        assert not at.exception, at.exception
        rec = [m.value for m in at.metric if m.label == "推荐转化窗口"]
        assert rec == ["S4"], f"{fam} 推荐窗口 {rec}，与报告 §5.3 的 S4 结论不符"
        print("[9] %s → 推荐窗口 %s" % (fam, rec[0]))
    assert any("胶乳" in x.value for x in at.caption), "缺少窗口卡 caption"

    print("\nALL CHECKS PASSED")


def test_tab2_crispron_source():
    """Tab2 单序列打分必须透出 CRISPRon 特征来源（P0：推理期特征伪造的防回归）。

    较慢（约 30 秒：DeepSpCas9 子进程 + WSL 内 CRISPRon 实跑），且需要 crispr conda 环境；
    WSL 不可用时走近似式降级路径，本用例同样应当通过——它断言的是"来源被如实标注"，
    而不是"必须拿到真实值"。
    """
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    assert not at.exception, at.exception

    at.text_area[0].set_value(PROBE_SEQ30).run()
    assert not at.exception, at.exception
    next(b for b in at.button if b.label == "打分").set_value(True).run()
    assert not at.exception, at.exception

    # Tab1 也渲染 dataframe，故按列名定位 Tab2 的结果表而不是按下标
    res = next((d.value for d in at.dataframe if "CRISPRon 来源" in list(d.value.columns)), None)
    assert res is not None, "Tab2 未渲染含「CRISPRon 来源」列的结果表"
    src = res["CRISPRon 来源"].tolist()
    assert src and all(s in SRC_LABELS.values() for s in src), src

    degraded = any(s == SRC_LABELS["approximated"] for s in src)
    if degraded:
        assert any("近似式降级值" in w.value for w in at.warning), "降级却未向用户告警"
        print("[T2] 降级路径：CRISPRon 来源 = 近似式降级，且已如实告警")
    else:
        assert any("真实模型实跑" in c.value for c in at.caption), "真实路径缺少来源说明"
        print("[T2] 真实路径：CRISPRon 经 WSL 实跑，来源已标注")
    print("[T2] 打分结果：%s" % res.to_dict("records"))


def test_tab2_excel_batch_import():
    """验证 Tab2 从 Excel 表格批量导入、智能列解析与预检质检指标展示。"""
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, at.exception

    # 切换至 Excel 批量导入分支
    assert len(at.segmented_control) >= 2, "缺少检测模式 segmented_control"
    at.segmented_control[1].set_value("从 Excel / CSV 表格批量导入").run()
    assert not at.exception, at.exception

    # 验证模板下载与文件上传器已渲染
    assert len(at.file_uploader) > 0, "缺少批量文件上传器组件"
    assert any("下载 Excel 导入模板" in b.label for b in at.download_button), "缺少 Excel 模板下载按钮"

    # 构造带有 2 条合规 + 1 条异常的 Excel 文件
    test_df = pd.DataFrame({
        "靶点编号": ["Guide_01", "Guide_02_Bad", "Guide_03"],
        "30bp靶位点序列": [
            "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
            "ATCG_TOO_SHORT",
            "ATTCGGCGTTAGATTGACAGAAGACGGTGG",
        ],
        "注释": ["测试1", "测试2", "测试3"],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        test_df.to_excel(writer, index=False)
    excel_bytes = buf.getvalue()

    # 模拟上传文件并重新运行
    at.file_uploader[0].upload("mock_targets.xlsx", excel_bytes).run()
    assert not at.exception, at.exception

    # 验证即时质检指标
    metrics = {m.label: m.value for m in at.metric}
    assert metrics.get("表格数据总行数") in ("3", 3), f"总行数异常: {metrics}"
    assert metrics.get("合规有效序列数") in ("2", 2), f"有效数异常: {metrics}"
    assert metrics.get("格式异常行数") in ("1", 1), f"异常数异常: {metrics}"

    # 验证批量打分按钮存在
    batch_btn = next((b for b in at.button if "开始批量检测打分" in b.label), None)
    assert batch_btn is not None, "缺少开始批量检测打分按钮"

    print("[T2-Batch] Excel 批量导入组件渲染、列探测、质检指标与按钮验证全量通过！")


def test_tab1_atac_annotations():
    """Tab1 应透出 ATAC 整合状态、默认注释列与「组织优先指数+ATAC加权」排序（折中方案）。"""
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, at.exception

    assert any("ATAC-seq 染色质开放峰" in x.value for x in at.info), "缺少 ATAC 整合状态提示"

    top = at.dataframe[0].value
    assert len(top) > 0, "默认基因的 Top10 表为空"
    for frag in ("ATAC状态", "ATAC开放峰内", "ATAC可及性分"):
        assert any(frag in c for c in top.columns), f"缺少 {frag} 列；现有 {list(top.columns)}"

    atac_opt = next((o for o in at.selectbox[1].options if o.startswith("组织优先指数+ATAC")), None)
    assert atac_opt is not None, at.selectbox[1].options
    at.selectbox[1].set_value(atac_opt).run()
    assert not at.exception, at.exception
    assert any("组织优先指数+ATAC" in c for c in at.dataframe[0].value.columns), \
        "ATAC 加权排序未产出加权分数列"
    print("[T1-ATAC] 状态提示 + 默认注释列 + ATAC 加权排序验证通过")


if __name__ == "__main__":
    test_app_dashboard()
    print()
    test_tab1_atac_annotations()
    print()
    test_tab2_excel_batch_import()
    print()
    test_tab2_crispron_source()

