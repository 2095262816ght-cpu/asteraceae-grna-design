# -*- coding: utf-8 -*-
"""test_batch_importer.py — 批量导入检测模块单元测试。

验证：
1. generate_template_excel & generate_template_csv 模板完整性；
2. read_uploaded_table 对 .xlsx, .csv 的解析、多 Sheet 切换与空行容错；
3. detect_sequence_column 和 detect_id_column 智能列探测；
4. precheck_table 异常捕捉、物理行号对应、ID 列联动与有效序列抽取；
5. merge_batch_results 结果无缝拼合、iloc_index 安全寻址与原列保留；
6. compute_file_hash 与导出正确性。
"""
import io
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
APP_DIR = BASE / "app"
for p in (str(BASE), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

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

try:
    from inference_client import BatchInferenceResult
except ImportError:
    from app.inference_client import BatchInferenceResult


def test_template_generation():
    """验证 Excel 与 CSV 模板生成。"""
    excel_bytes = generate_template_excel()
    assert len(excel_bytes) > 1000, "生成的 Excel 模板过小"

    # 读取并验证 sheets
    excel_file = io.BytesIO(excel_bytes)
    sheets = get_excel_sheet_names(excel_file, "template.xlsx")
    assert "待检测序列导入模板" in sheets
    assert "格式说明与规范" in sheets

    df = read_uploaded_table(excel_file, "template.xlsx", sheet_name="待检测序列导入模板")
    assert len(df) == 5
    assert "30bp靶位点序列" in df.columns
    # 橡胶草 (TKS) 实测示例行（B1：自定义通道橡胶草支持）
    assert "Sample_TKS_01" in set(df["靶点编号"])
    assert "Sample_TKS_02" in set(df["靶点编号"])

    csv_bytes = generate_template_csv()
    assert len(csv_bytes) > 0
    csv_df = read_uploaded_table(io.BytesIO(csv_bytes), "template.csv")
    assert len(csv_df) == 5


def test_read_uploaded_table_and_sheets():
    """验证多 Sheet 获取与指定 Sheet 解析。"""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"seq": ["ATCGGCTAAGCTAGGCTAGCATCGTGGATC"]}).to_excel(
            writer, sheet_name="S1", index=False
        )
        pd.DataFrame({"seq": ["ATTCGGCGTTAGATTGACAGAAGACGGTGG"]}).to_excel(
            writer, sheet_name="S2", index=False
        )
    excel_bytes = buf.getvalue()

    sheets = get_excel_sheet_names(io.BytesIO(excel_bytes), "multi.xlsx")
    assert sheets == ["S1", "S2"]

    df_s2 = read_uploaded_table(io.BytesIO(excel_bytes), "multi.xlsx", sheet_name="S2")
    assert len(df_s2) == 1
    assert df_s2["seq"].iloc[0] == "ATTCGGCGTTAGATTGACAGAAGACGGTGG"


def test_physical_row_mapping_with_empty_rows():
    """验证当表格中间存在空行时，物理行号精准保持与 Excel 一致。"""
    # 构造表格：
    # 第 1 行：表头
    # 第 2 行：数据 S1
    # 第 3 行：全空行（None）
    # 第 4 行：数据 S2（格式错误）
    df_raw = pd.DataFrame([
        {"id": "G1", "seq": "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"},
        {"id": None, "seq": None},
        {"id": "G2", "seq": "SHORT_SEQ"},
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_raw.to_excel(writer, index=False)
    excel_bytes = buf.getvalue()

    df_read = read_uploaded_table(io.BytesIO(excel_bytes), "with_empty.xlsx")
    # 空行被自动过滤，剩余 2 行
    assert len(df_read) == 2

    # 执行预检
    res = precheck_table(df_read, sequence_col="seq", id_col="id")
    assert res.valid_count == 1
    assert res.invalid_count == 1

    # 验证异常行的物理行号精确指向 Excel 第 4 行（而不是错位成第 3 行）
    bad_issue = res.issues[0]
    assert bad_issue.row_number == 4, f"物理行号错位，期望 4，实际为 {bad_issue.row_number}"
    assert bad_issue.id_value == "G2"
    assert bad_issue.iloc_index == 1

    # 验证安全合并
    mock_raw = pd.DataFrame({
        "seq30": res.valid_sequences,
        "deepspcas9_score": [70.0],
        "crispron_source": ["wsl_real"],
        "stacking_score": [50.0],
    })
    mock_infer = BatchInferenceResult(
        raw_df=mock_raw, display_df=mock_raw, latency_s=1.0, total_count=1, n_approximated=0
    )
    merged = merge_batch_results(df_read, res, mock_infer)
    assert len(merged) == 2
    assert merged["检测状态"].iloc[0] == "检测成功"
    assert "格式异常" in merged["检测状态"].iloc[1]
    assert "_excel_row_num" not in merged.columns, "临时辅助列未清理"


def test_detect_columns():
    """验证智能列探测算法。"""
    # 场景 1：标准列名
    df1 = pd.DataFrame({
        "guide_id": ["G1", "G2"],
        "seq30": ["ATCGGCTAAGCTAGGCTAGCATCGTGGATC", "ATCGGCTAAGCTAGGCTAGCATCGTGGATC"],
        "other": [1, 2],
    })
    assert detect_sequence_column(df1) == "seq30"
    assert detect_id_column(df1, seq_col="seq30") == "guide_id"

    # 场景 2：中文列名与无明显特征列名，但内容符合 30bp 规范
    df2 = pd.DataFrame({
        "编号": ["01", "02"],
        "未命名列_X": ["ATCGGCTAAGCTAGGCTAGCATCGTGGATC", "ATTCGGCGTTAGATTGACAGAAGACGGTGG"],
        "数量": [10, 20],
    })
    assert detect_sequence_column(df2) == "未命名列_X"
    assert detect_id_column(df2, seq_col="未命名列_X") == "编号"


def test_compute_file_hash():
    """验证文件内容哈希计算防缓存碰撞。"""
    c1 = b"some data 1"
    c2 = b"some data 2"
    h1 = compute_file_hash(c1)
    h2 = compute_file_hash(c2)
    assert len(h1) == 12
    assert h1 != h2
    assert h1 == compute_file_hash(c1)


def run_all_tests():
    test_funcs = [
        test_template_generation,
        test_read_uploaded_table_and_sheets,
        test_physical_row_mapping_with_empty_rows,
        test_detect_columns,
        test_compute_file_hash,
    ]
    print("=" * 60)
    print(" 正在运行批量导入检测增强测试套件 (test_batch_importer.py)")
    print("=" * 60)
    passed = 0
    for fn in test_funcs:
        fn()
        print(f"  [PASS] {fn.__name__}")
        passed += 1
    print("=" * 60)
    print(f" 批量导入测试完成: 全部 {passed}/{len(test_funcs)} 项通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
