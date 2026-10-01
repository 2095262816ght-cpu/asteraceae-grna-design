# -*- coding: utf-8 -*-
"""batch_session.py — 批量打分生命周期深度模块（demo Tab-2 批量流的唯一属主）。

接口：上传表 → 校验批次 → 打分 + 拼装结果集（+ 可选 ATAC 标注）。
实现隐藏：防碰撞缓存键构成、动态超时策略、推理调用与结果拼装、ATAC 展示转换。
batch_importer 是本模块的 IO 适配器（读表 / 列探测 / 预检 / 模板 / 导出），不含生命周期策略。
零 Streamlit 依赖，可独立单元测试。
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import pandas as pd

try:
    from batch_importer import (
        TablePrecheckResult,
        compute_file_hash,
        merge_batch_results,
        precheck_table,
        read_uploaded_table,
    )
    from inference_client import BatchInferenceResult, InferenceClient
    from core.atac_annotator import (
        COL_IN_PEAK,
        COL_STATUS,
        STATUS_NEAR,
        AtacAtlas,
        annotate_guides,
        to_display_df,
    )
except ImportError:
    from cs_pipeline.app.batch_importer import (
        TablePrecheckResult,
        compute_file_hash,
        merge_batch_results,
        precheck_table,
        read_uploaded_table,
    )
    from cs_pipeline.app.inference_client import BatchInferenceResult, InferenceClient
    from cs_pipeline.core.atac_annotator import (
        COL_IN_PEAK,
        COL_STATUS,
        STATUS_NEAR,
        AtacAtlas,
        annotate_guides,
        to_display_df,
    )


@dataclass
class AtacAnnotation:
    """ATAC 标注结果：展示表 + 计数指标。"""

    display_df: pd.DataFrame
    n_in_peak: int
    n_near: int


def _scoring_timeout_s(valid_count: int) -> int:
    """动态超时策略：固定启动开销下限 + 随条数线性放宽。"""
    return max(180, valid_count * 5 + 60)


class BatchScoringSession:
    """批量打分生命周期：上传表 → 校验批次 → 打分 + ATAC 标注结果集。

    构造参数是 UI 决策结果（工作表、序列列、ID 列）；过程策略全部内聚，
    调用方只需要按 load → precheck → run（→ annotate_atac）顺序推进。
    """

    def __init__(
        self,
        file_bytes: bytes,
        filename: str,
        sheet_name: str | None,
        seq_col: str,
        id_col: str | None = None,
    ):
        self._file_bytes = file_bytes
        self.filename = filename
        self.sheet_name = sheet_name
        self.seq_col = seq_col
        self.id_col = id_col

    @property
    def cache_key(self) -> str:
        """防碰撞缓存键：文件哈希 + 工作表 + 序列列 + ID 列构成。"""
        return "_".join(
            [compute_file_hash(self._file_bytes), str(self.sheet_name), str(self.seq_col), str(self.id_col)]
        )

    def load(self) -> pd.DataFrame:
        """上传表 → 原始 DataFrame（IO 适配委托 batch_importer）。"""
        return read_uploaded_table(io.BytesIO(self._file_bytes), self.filename, sheet_name=self.sheet_name)

    def precheck(self, raw_df: pd.DataFrame) -> TablePrecheckResult:
        """校验批次：序列规格预检（IO 适配委托 batch_importer）。"""
        return precheck_table(raw_df, self.seq_col, id_col=self.id_col)

    def run(
        self,
        raw_df: pd.DataFrame,
        precheck: TablePrecheckResult,
        client: InferenceClient,
    ) -> tuple[BatchInferenceResult, pd.DataFrame]:
        """打分 + 拼装结果集：动态超时策略与结果合并内聚于此。"""
        infer_res = client.score_sequences(
            precheck.valid_sequences,
            timeout_s=_scoring_timeout_s(len(precheck.valid_sequences)),
        )
        return infer_res, merge_batch_results(raw_df, precheck, infer_res)

    def annotate_atac(
        self,
        merged_df: pd.DataFrame,
        atlas: AtacAtlas,
        chrom_col: str,
        start_col: str,
        end_col: str,
    ) -> AtacAnnotation:
        """ATAC 标注 + 展示转换（展示语义单点定义在 core.atac_annotator.to_display_df）。"""
        annotated = annotate_guides(
            merged_df, atlas, chrom_col=chrom_col, start_col=start_col, end_col=end_col
        )
        return AtacAnnotation(
            display_df=to_display_df(annotated),
            n_in_peak=int(annotated[COL_IN_PEAK].sum()),
            n_near=int((annotated[COL_STATUS] == STATUS_NEAR).sum()),
        )
