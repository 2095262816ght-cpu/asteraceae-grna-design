# -*- coding: utf-8 -*-
"""batch_importer.py — Excel / CSV 表格批量导入检测深度模块。

提供批量 gRNA 序列表格的读取、工作表选择、列智能探测、格式预检校验、打分结果拼装与模板生成导出。
设计遵循深度模块原则：逻辑高内聚、零 Streamlit 依赖，可独立进行单元测试。
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

try:
    from core.sequence_spec import validate_seq30
except ImportError:
    from cs_pipeline.core.sequence_spec import validate_seq30

try:
    from inference_client import BatchInferenceResult, COL_DISPLAY_MAP, SRC_LABELS
except ImportError:
    try:
        from app.inference_client import BatchInferenceResult, COL_DISPLAY_MAP, SRC_LABELS
    except ImportError:
        from cs_pipeline.app.inference_client import BatchInferenceResult, COL_DISPLAY_MAP, SRC_LABELS


# 常见序列列名候选（按优先级与权重排序）
SEQ_COLUMN_KEYWORDS = [
    "seq30",
    "30bp",
    "target_site",
    "靶位点",
    "靶点序列",
    "30bp序列",
    "sequence",
    "seq",
    "序列",
    "guide_seq",
    "grna_seq",
    "target",
    "guide",
]

# 常见 ID / 名称列候选
ID_COLUMN_KEYWORDS = [
    "guide_id",
    "id",
    "gene_id",
    "gene",
    "靶点编号",
    "靶点id",
    "编号",
    "序号",
    "名称",
    "name",
    "target_id",
]

# 规范示例序列（真实可打分样本）
SAMPLE_RECORDS = [
    {
        "靶点编号": "Sample_Guide_01",
        "30bp靶位点序列": "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
        "目标基因": "LsaT2T01G023690",
        "备注": "NLR家族标准示范靶点",
    },
    {
        "靶点编号": "Sample_Guide_02",
        "30bp靶位点序列": "ATTCGGCGTTAGATTGACAGAAGACGGTGG",
        "目标基因": "LsaT2T01G023690",
        "备注": "高特异性外显子靶点",
    },
    {
        "靶点编号": "Sample_Guide_03",
        "30bp靶位点序列": "CGTACGTTGCTAGCTAGCTAGCATCGGGCA",
        "目标基因": "LsaT2T06G019420",
        "备注": "高表达适宜靶向位点",
    },
    {
        "靶点编号": "Sample_TKS_01",
        "30bp靶位点序列": "ATATGAAAATGTCAGGATGCCTGAAGGACA",
        "目标基因": "EVM.MODEL.LG07.3296",
        "备注": "橡胶草 (TKS) 实测靶点 · Hi-TOM 金标准来源",
    },
    {
        "靶点编号": "Sample_TKS_02",
        "30bp靶位点序列": "TGGAAGAGTCGCCCCTGTTGATTCTGGATT",
        "目标基因": "EVM.MODEL.LG07.3933",
        "备注": "橡胶草 (TKS) 实测靶点 · Hi-TOM 金标准来源",
    },
]


@dataclass(frozen=True)
class ValidationIssue:
    """单条序列校验异常记录。"""
    iloc_index: int       # DataFrame 内部索引，用于安全精准回填
    row_number: int       # 对应 Excel 表中的物理行号（含表头）
    raw_value: str
    error_message: str
    id_value: str | None = None  # 关联的靶点ID或名称（若有）


@dataclass(frozen=True)
class TablePrecheckResult:
    """表格预检分析结果结构体。"""
    total_rows: int
    valid_count: int
    invalid_count: int
    valid_indices: list[int]
    valid_sequences: list[str]
    issues: list[ValidationIssue]
    sequence_col: str
    id_col: str | None = None

    @property
    def has_issues(self) -> bool:
        return self.invalid_count > 0

    @property
    def all_valid(self) -> bool:
        return self.invalid_count == 0 and self.valid_count > 0


def compute_file_hash(content: bytes) -> str:
    """计算上传文件字节内容的 MD5 哈希摘要（前 12 位），用于防脏读缓存。"""
    return hashlib.md5(content).hexdigest()[:12]


def get_excel_sheet_names(file_bytes_or_buffer, filename: str) -> list[str]:
    """获取 Excel 文件内包含的所有工作表名称。"""
    name_lower = filename.lower()
    if name_lower.endswith((".xlsx", ".xls")):
        try:
            if hasattr(file_bytes_or_buffer, "seek"):
                file_bytes_or_buffer.seek(0)
            xl = pd.ExcelFile(file_bytes_or_buffer)
            if hasattr(file_bytes_or_buffer, "seek"):
                file_bytes_or_buffer.seek(0)
            return list(xl.sheet_names)
        except Exception:
            return ["Sheet1"]
    return ["默认工作表"]


def _score_columns_by_keywords(
    cols: Sequence[str], keywords: Sequence[str], base_score: float
) -> dict[str, float]:
    """消除重复：根据关键词列表对表格列名进行权重打分。"""
    scores = {c: 0.0 for c in cols}
    for col in cols:
        col_lower = str(col).lower()
        for idx, kw in enumerate(keywords):
            if kw in col_lower:
                scores[col] += max(base_score - idx * 2.0, 10.0)
                break
    return scores


def read_uploaded_table(
    file_bytes_or_buffer, filename: str, sheet_name: str | None = None
) -> pd.DataFrame:
    """自适应读取用户上传的 Excel (.xlsx, .xls) 或 CSV 表格文件。
    
    精准记录原始文件的物理行号 `_excel_row_num`，并对空行与格式进行健壮性预处理。
    """
    if isinstance(file_bytes_or_buffer, bytes):
        file_bytes_or_buffer = io.BytesIO(file_bytes_or_buffer)

    if hasattr(file_bytes_or_buffer, "seek"):
        file_bytes_or_buffer.seek(0)

    name_lower = filename.lower()
    if name_lower.endswith((".xlsx", ".xls")):
        try:
            target_sheet = sheet_name if sheet_name else 0
            df = pd.read_excel(file_bytes_or_buffer, sheet_name=target_sheet)
        except Exception as exc:
            raise ValueError(f"读取 Excel 文件失败，请确认文件未损坏且格式标准: {exc}") from exc
    elif name_lower.endswith(".csv"):
        if hasattr(file_bytes_or_buffer, "getvalue"):
            raw_bytes = file_bytes_or_buffer.getvalue()
        elif hasattr(file_bytes_or_buffer, "read"):
            raw_bytes = file_bytes_or_buffer.read()
        else:
            raw_bytes = bytes(file_bytes_or_buffer)
        encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
        df = None
        last_err = None
        for enc in encodings:
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc)
                break
            except Exception as err:
                last_err = err
                continue
        if df is None:
            raise ValueError(f"读取 CSV 文件编码失败（已尝试 utf-8/gbk）: {last_err}")
    else:
        raise ValueError("仅支持 .xlsx, .xls 或 .csv 格式的表格文件。")

    if hasattr(file_bytes_or_buffer, "seek"):
        file_bytes_or_buffer.seek(0)

    # 清理列名首尾空格
    df.columns = [str(c).strip() for c in df.columns]

    # 记录物理行号（考虑表头占第 1 行，数据行自第 2 行开始）
    df["_excel_row_num"] = [i + 2 for i in range(len(df))]

    # 去除纯空行（排除我们插入的行号辅助列）
    content_cols = [c for c in df.columns if c != "_excel_row_num"]
    df = df.dropna(how="all", subset=content_cols).copy()
    if df.empty:
        raise ValueError("上传的表格内容为空，请检查后重新上传。")

    # 重新连续切片并保留物理行号
    df = df.reset_index(drop=True)
    return df


def detect_sequence_column(df: pd.DataFrame) -> str:
    """智能探测 DataFrame 中最可能包含 30bp 靶位点序列的列。"""
    cols = [c for c in df.columns if c != "_excel_row_num"]
    if not cols:
        raise ValueError("表格没有任何有效列。")

    # 1. 列名关键词匹配得分
    scores = _score_columns_by_keywords(cols, SEQ_COLUMN_KEYWORDS, base_score=50.0)

    # 2. 列内容特征采样打分（复用领域单点校验 validate_seq30）
    for col in cols:
        series_sample = df[col].dropna().astype(str).str.strip().str.upper()
        if len(series_sample) > 0:
            sample_sub = series_sample.head(20)
            # 严格合规比例（直接调用 core.sequence_spec.validate_seq30）
            valid_ratio = sample_sub.apply(lambda s: validate_seq30(s) is None).mean()
            len_30_ratio = (sample_sub.str.len() == 30).mean()

            scores[col] += valid_ratio * 70.0 + len_30_ratio * 30.0

    best_col = max(scores, key=lambda k: scores[k])
    return best_col


def detect_id_column(df: pd.DataFrame, seq_col: str | None = None) -> str | None:
    """智能探测 DataFrame 中最可能作为标识/ID/名称的列。"""
    cols = [c for c in df.columns if c not in (seq_col, "_excel_row_num")]
    if not cols:
        return None

    scores = _score_columns_by_keywords(cols, ID_COLUMN_KEYWORDS, base_score=40.0)
    best_col = max(scores, key=lambda k: scores[k])
    if scores[best_col] > 0.0:
        return best_col
    return None


def precheck_table(
    df: pd.DataFrame, sequence_col: str, id_col: str | None = None
) -> TablePrecheckResult:
    """对选定序列列进行全面合法性预检与问题归类。"""
    if sequence_col not in df.columns:
        raise ValueError(f"指定的序列列 '{sequence_col}' 不存在于表格中。")

    has_id = bool(id_col and id_col in df.columns)
    total_rows = len(df)
    valid_indices: list[int] = []
    valid_sequences: list[str] = []
    issues: list[ValidationIssue] = []

    for row_idx in range(total_rows):
        val = df[sequence_col].iloc[row_idx]
        # 优先读取真实的 Excel 物理行号
        excel_row_num = (
            int(df["_excel_row_num"].iloc[row_idx])
            if "_excel_row_num" in df.columns
            else row_idx + 2
        )
        id_val = str(df[id_col].iloc[row_idx]).strip() if has_id and pd.notna(df[id_col].iloc[row_idx]) else None

        if pd.isna(val) or str(val).strip() == "":
            issues.append(
                ValidationIssue(
                    iloc_index=row_idx,
                    row_number=excel_row_num,
                    raw_value="（空值）",
                    error_message="序列为空，必须为 30bp 完整靶位点",
                    id_value=id_val,
                )
            )
            continue

        raw_str = str(val).strip().upper()
        err = validate_seq30(raw_str)
        if err is not None:
            issues.append(
                ValidationIssue(
                    iloc_index=row_idx,
                    row_number=excel_row_num,
                    raw_value=raw_str,
                    error_message=err,
                    id_value=id_val,
                )
            )
        else:
            valid_indices.append(row_idx)
            valid_sequences.append(raw_str)

    return TablePrecheckResult(
        total_rows=total_rows,
        valid_count=len(valid_sequences),
        invalid_count=len(issues),
        valid_indices=valid_indices,
        valid_sequences=valid_sequences,
        issues=issues,
        sequence_col=sequence_col,
        id_col=id_col,
    )


def merge_batch_results(
    raw_df: pd.DataFrame,
    precheck: TablePrecheckResult,
    inference_result: BatchInferenceResult,
) -> pd.DataFrame:
    """将批量推理预测结果与用户原始表格进行完整合并保留。
    
    使用强类型 `iloc_index` 直接寻址更新，杜绝行号反推导致的索引偏移；
    清理内部行号标记，完整保留用户原始列。
    """
    out_df = raw_df.copy()
    if "_excel_row_num" in out_df.columns:
        out_df = out_df.drop(columns=["_excel_row_num"])

    # 初始化新增的结果列
    status_col = ["未打分"] * len(out_df)
    deepspcas9_col: list[float | str] = ["-"] * len(out_df)
    crispron_src_col: list[str] = ["-"] * len(out_df)
    stacking_score_col: list[float | str] = ["-"] * len(out_df)

    # 1. 标记格式异常项（使用 iloc_index 确保 100% 精准对应）
    for issue in precheck.issues:
        if 0 <= issue.iloc_index < len(out_df):
            status_col[issue.iloc_index] = f"格式异常：{issue.error_message}"

    # 2. 填入有效项的预测值（使用 valid_indices 切片对应）
    res_raw = inference_result.raw_df
    for local_idx, orig_idx in enumerate(precheck.valid_indices):
        if local_idx < len(res_raw):
            row_res = res_raw.iloc[local_idx]
            status_col[orig_idx] = "检测成功"
            deepspcas9_col[orig_idx] = float(row_res["deepspcas9_score"])
            src_val = str(row_res["crispron_source"])
            crispron_src_col[orig_idx] = SRC_LABELS.get(src_val, src_val)
            stacking_score_col[orig_idx] = float(row_res["stacking_score"])

    # 组织输出列（在原表后面追加结果列）
    out_df["检测状态"] = status_col
    out_df["DeepSpCas9 分数"] = deepspcas9_col
    out_df["CRISPRon 来源"] = crispron_src_col
    out_df["Stacking 集成效率分"] = stacking_score_col

    return out_df


def generate_template_excel() -> bytes:
    """生成包含格式说明与标准 30bp 序列示例的 Excel 模板。"""
    output = io.BytesIO()
    sample_df = pd.DataFrame(SAMPLE_RECORDS)
    readme_df = pd.DataFrame([
        {
            "字段名称": "靶点编号 (可选)",
            "说明": "用户自定义的 gRNA 或靶位点唯一标识，用于区分实验样本。",
            "示例": "Sample_Guide_01",
        },
        {
            "字段名称": "30bp靶位点序列 (必填)",
            "说明": "严格 30bp 序列，布局为：4nt 5'上游 + 20nt guide + 3nt PAM(须为NGG) + 3nt 3'下游。仅允许 A/C/G/T。",
            "示例": "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
        },
        {
            "字段名称": "目标基因 (可选)",
            "说明": "宿主基因编号或 NLR 基因座 ID，便于结果筛选与下游对照。",
            "示例": "LsaT2T01G023690",
        },
        {
            "字段名称": "备注 (可选)",
            "说明": "任何实验注释、组织偏好或靶向策略说明，打分结果将完整保留此列。",
            "示例": "外显子功能区候选",
        },
        {
            "字段名称": "物种支持说明",
            "说明": "支持任意物种 30bp 靶位点（橡胶草 / 莴苣等）。v2.1 生产模型以橡胶草 Hi-TOM 实测金标准训练，橡胶草序列属同物种对口预测；效率分为同一基因内候选的相对排序参考，非绝对 indel% 承诺。",
            "示例": "Sample_TKS_01 / Sample_TKS_02 为橡胶草实测示例",
        },
    ])

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample_df.to_excel(writer, sheet_name="待检测序列导入模板", index=False)
        readme_df.to_excel(writer, sheet_name="格式说明与规范", index=False)

    return output.getvalue()


def generate_template_csv() -> bytes:
    """生成标准 CSV 模板（utf-8-sig 编码）。"""
    sample_df = pd.DataFrame(SAMPLE_RECORDS)
    return sample_df.to_csv(index=False).encode("utf-8-sig")


def export_dataframe_to_excel(df: pd.DataFrame, sheet_name: str = "gRNA批量检测结果") -> bytes:
    """将预测完成的结果 DataFrame 导出为带样式的 Excel 字节流。"""
    output = io.BytesIO()
    clean_df = df.drop(columns=["_excel_row_num"], errors="ignore")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        clean_df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def export_dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """将预测完成的结果 DataFrame 导出为 UTF-8-SIG CSV 字节流。"""
    clean_df = df.drop(columns=["_excel_row_num"], errors="ignore")
    return clean_df.to_csv(index=False).encode("utf-8-sig")
