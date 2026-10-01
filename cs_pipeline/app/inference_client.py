# -*- coding: utf-8 -*-
"""inference_client.py — 跨环境模型推理客户端接缝模块。

封装针对 independent crispr conda 环境的模型推理子进程调用（score_deepspcas9_cli.py），
隐藏 Python 解释器搜索、Windows DLL PATH 注入、IPC 协议行通信与降级标注细节。
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

try:
    from scripts.crispron_scorer import SOURCE_APPROXIMATED, SOURCE_WSL_REAL
except ImportError:
    from cs_pipeline.scripts.crispron_scorer import SOURCE_APPROXIMATED, SOURCE_WSL_REAL

SRC_LABELS = {
    SOURCE_WSL_REAL: "真实模型实跑（WSL/容器原生）",
    SOURCE_APPROXIMATED: "⚠️ 近似式降级",
}

COL_DISPLAY_MAP = {
    "seq30": "30bp 序列",
    "deepspcas9_score": "DeepSpCas9 分数",
    "crispron_score": "CRISPRon 分数",
    "crispron_source": "CRISPRon 来源",
    "stacking_score": "Stacking 集成效率分",
}


class InferenceError(Exception):
    """推理接口通用异常基类。"""


class InferenceTimeoutError(InferenceError):
    """推理子进程超时。"""


class InferenceEnvironmentError(InferenceError):
    """无法找到或启动推理环境 Python 解释器。"""


class InferenceExecutionError(InferenceError):
    """推理子进程返回非零退出码。"""


@dataclass(frozen=True)
class BatchInferenceResult:
    """批量推理结果结构化视图。"""
    raw_df: pd.DataFrame
    display_df: pd.DataFrame
    latency_s: float
    total_count: int
    n_approximated: int

    @property
    def has_approximated(self) -> bool:
        return self.n_approximated > 0

    @property
    def warning_message(self) -> str | None:
        if not self.has_approximated:
            return None
        return (
            f"其中 **{self.n_approximated}/{self.total_count} 条**的 CRISPRon 特征是**经验近似式降级值**，"
            f"非真实模型输出（原因：CRISPRon 管线不可用，或该序列的正反链窗口与输入不完全匹配）。"
            f"近似式与真实值实测可偏约 15%，这些行的集成效率分仅供粗略参考。"
        )

    @property
    def caption_message(self) -> str:
        if self.has_approximated:
            return "部分特征为降级值，详见上方警示。"
        return "CRISPRon 特征全部经真实模型实跑产出（WSL/容器原生管线），与训练集同一管线、同一取值约定。"


class InferenceClient:
    """深度模块：管理跨进程模型推理生命周期。"""

    def __init__(
        self,
        crispr_python: str | None = None,
        cli_script: Path | str | None = None,
        default_timeout_s: int = 120,
    ):
        self.default_timeout_s = default_timeout_s
        self._base_dir = Path(__file__).resolve().parent.parent
        self._cli_script = Path(cli_script) if cli_script else self._base_dir / "app" / "score_deepspcas9_cli.py"
        self._crispr_python = crispr_python or self._resolve_crispr_python()

    def _resolve_crispr_python(self) -> str:
        """多级探测 crispr 环境的 python.exe 路径。"""
        explicit = os.environ.get("CRISPR_PYTHON")
        if explicit and Path(explicit).exists():
            return explicit

        cur_exe = Path(sys.executable)
        candidates = [
            cur_exe.parent.parent / "envs" / "crispr" / "python.exe",
            cur_exe.parent.parent / "crispr" / "python.exe",
            Path(r"D:\Miniconda\envs\crispr\python.exe"),
            Path.home() / "miniconda3" / "envs" / "crispr" / "python.exe",
            Path.home() / "anaconda3" / "envs" / "crispr" / "python.exe",
            Path(r"C:\miniconda3\envs\crispr\python.exe"),
            Path(r"C:\anaconda3\envs\crispr\python.exe"),
            Path(r"C:\ProgramData\miniconda3\envs\crispr\python.exe"),
            Path(r"C:\ProgramData\anaconda3\envs\crispr\python.exe"),
        ]
        conda_p1 = os.environ.get("CONDA_PREFIX_1")
        if conda_p1:
            candidates.append(Path(conda_p1) / "envs" / "crispr" / "python.exe")

        for cand in candidates:
            if cand.exists():
                return str(cand)

        return "python"

    def _build_env(self) -> dict[str, str]:
        """构建带有 Windows DLL 依赖路径的环境变量。"""
        env = os.environ.copy()
        if self._crispr_python != "python":
            py_dir = Path(self._crispr_python).parent
            lib_bin = py_dir / "Library" / "bin"
            if lib_bin.exists():
                env["PATH"] = f"{lib_bin}{os.pathsep}{py_dir}{os.pathsep}{env.get('PATH', '')}"
        return env

    def score_sequences(
        self,
        sequences: Sequence[str],
        timeout_s: int | None = None,
    ) -> BatchInferenceResult:
        """执行批量序列打分。
        
        参数:
            sequences: 30bp 序列集合（字符串列表）。
            timeout_s: 单次调用超时限制（秒），默认采用类初始化配置。
            
        返回:
            BatchInferenceResult 结构化结果。
            
        异常:
            InferenceTimeoutError, InferenceEnvironmentError, InferenceExecutionError
        """
        seqs = [s.strip().upper() for s in sequences if s.strip()]
        if not seqs:
            empty_df = pd.DataFrame(columns=list(COL_DISPLAY_MAP.keys()))
            return BatchInferenceResult(
                raw_df=empty_df,
                display_df=empty_df.rename(columns=COL_DISPLAY_MAP),
                latency_s=0.0,
                total_count=0,
                n_approximated=0,
            )

        timeout = timeout_s or self.default_timeout_s
        input_data = "\n".join(seqs) + "\n"
        env = self._build_env()

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [self._crispr_python, str(self._cli_script)],
                input=input_data,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise InferenceTimeoutError(f"打分超时（>{timeout} s），请减少序列条数后重试。") from exc
        except FileNotFoundError as exc:
            raise InferenceEnvironmentError(f"找不到打分环境的 Python 解释器 ({self._crispr_python})。") from exc
        except Exception as exc:
            raise InferenceExecutionError(f"打分子进程启动失败: {exc}") from exc

        elapsed = time.perf_counter() - t0

        if proc.returncode != 0:
            err_msg = proc.stderr[-2000:] if proc.stderr else "（无错误输出）"
            raise InferenceExecutionError(f"打分子进程失败 (退出码 {proc.returncode}):\n{err_msg}")

        try:
            scores_raw = pd.read_csv(io.StringIO(proc.stdout))
        except Exception as exc:
            raise InferenceExecutionError(f"解析打分产物 CSV 失败: {exc}\n输出内容:\n{proc.stdout[:500]}") from exc

        # 统计并格式化降级标签
        n_approx = 0
        scores_display = scores_raw.copy()
        if "crispron_source" in scores_display.columns:
            n_approx = int((scores_display["crispron_source"] == SOURCE_APPROXIMATED).sum())
            scores_display["crispron_source"] = [
                SRC_LABELS.get(str(v), str(v)) for v in scores_display["crispron_source"]
            ]

        display_df = scores_display.rename(columns=COL_DISPLAY_MAP)

        return BatchInferenceResult(
            raw_df=scores_raw,
            display_df=display_df,
            latency_s=elapsed,
            total_count=len(scores_raw),
            n_approximated=n_approx,
        )
