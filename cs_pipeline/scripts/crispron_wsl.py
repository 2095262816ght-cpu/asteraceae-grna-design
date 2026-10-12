# -*- coding: utf-8 -*-
"""crispron_wsl.py — CRISPRon 真实打分的管线调用封装（交互推理用）。

为什么需要它
------------
训练集与 demo 候选库的 `crispron_score` 都由 `scripts/03_score_crispron.py` 经 WSL 管线
批量实跑产出。但交互推理路径 `scripts/predict.py` 此前无法调用该管线，改用
`deepspcas9*0.95 + (tm-50)*0.25` 的经验近似式**伪造**这一维特征（进度报告标记为 P0：
"推理期特征伪造"）。实测误差：对 demo Tab2 输入框预填的 placeholder 序列
`ATCGGCTAAGCTAGGCTAGCATCGTGGATC`，近似式给 68.27、WSL 真实值 59.61，
**偏 +8.66 分 / 相对 14.5%**，而该值会作为 10 维之一进入形态二 GLMM 影响最终展示分。

取值约定与 `scripts/03` 逐条一致（否则推理特征与训练特征不同源）：
  1. fasta 头为 guide 标识、序列为 30nt seq30；
  2. 解析产物 `crispron.csv` 的 `ID` / `30mer` / `CRISPRon` 三列；
  3. `ID` 去掉 `_[pm]_<数字>$` 后缀还原 guide 标识（p=正链、m=反链窗口）；
  4. **只保留 `30mer` 与输入 `seq30` 完全相等的行**——输入恰为 30nt 时正/反链各至多
     产生一个 30mer 窗口，该过滤保证每条输入恰好取到一个分数。
实测 29 条 distinct guide：产物 30 行（29 正链 + 1 反链），精确匹配 29 行，一一对应。

运行模式（CRISPRON_MODE 环境变量：auto | wsl | native，默认 auto）
---------------------------------------------------------------
- wsl：Windows 宿主机经 `wsl.exe` 调 WSL 内 conda `crispron` 环境（历史默认路径）。
- native：Linux/容器内直接 `bash bin/CRISPRon.sh`，PATH 前置 `CRISPRON_PYTHON`
  （默认 /opt/venv-crispron/bin/python3）所在目录，保证脚本 shebang `python3`
  解析到 TF2.14 环境；RNAfold 由 PATH 提供（bioconda viennarna 2.6.4）。
- auto：有 wsl.exe 走 wsl（Windows 行为逐字节不变），否则走 native。
两种模式的 fasta 写入与产物解析完全共享，取值口径不变。

依赖与降级
----------
wsl 模式需要 Windows 侧 `wsl.exe` + WSL 内 `Ubuntu-22.04` 发行版 + 该发行版内的
`crispron` conda 环境（由 `env/setup_crispron_wsl.sh` 组装）+ `tools/CRISPRon`。
native 模式需要 `bash` + `CRISPRON_PYTHON` 指向的 TF2.14 python3 + PATH 里有 RNAfold
+ `tools/CRISPRon`。任一缺失、超时或产物异常时 `score()` 返回空 dict；
**本模块绝不返回近似值冒充真实值**，降级决策与标注由调用方显式承担。

延迟实测（WSL 热身后）：首次 1 条 13.6 秒（含 WSL 冷启动）、29 条 8.2 秒——固定开销主导，
批量几乎不增本，故按块整批调用而非逐条调用（块大小 `CHUNK_SIZE`=500）。

一致性实测（29 条 distinct guide）：本模块算出的真实 CRISPRon 分数与**训练集里已存的
`crispron_score`（scripts/03 一次跑 1361 条产出）逐值相同**（最大绝对差 0.0000、相关
1.000000）——证明推理与训练取的是同一约定同一管线。跨次运行与跨分块方式的最大绝对差
≤0.01（均值 0.0007），来自产物 CSV 两位小数舍入处的 TF 浮点噪声，量级为满量程的 0.01%。
"""
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CRISPRON_DIR = BASE_DIR / "tools" / "CRISPRon"
WSL_DISTRO = "Ubuntu-22.04"
CONDA_ENV = "crispron"
DEFAULT_TIMEOUT_S = 90
# 单次 WSL 调用的序列上限。历史批量口径（scripts/03 跑训练集）为 1361 条，取 500 留足余量。
CHUNK_SIZE = 500

_ACTIVATE = f"source ~/miniconda3/etc/profile.d/conda.sh && conda activate {CONDA_ENV}"


def _mode() -> str:
    m = os.environ.get("CRISPRON_MODE", "auto").strip().lower()
    return m if m in ("auto", "wsl", "native") else "auto"


def _native_python() -> str:
    return os.environ.get("CRISPRON_PYTHON", "/opt/venv-crispron/bin/python3")


def _wsl_ready(timeout_s: int) -> bool:
    if shutil.which("wsl") is None:
        return False
    if not (CRISPRON_DIR / "bin" / "CRISPRon.sh").exists():
        return False
    try:
        r = subprocess.run(
            ["wsl", "-d", WSL_DISTRO, "bash", "-lc", f"{_ACTIVATE} && echo READY"],
            capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and b"READY" in r.stdout


def _native_ready() -> bool:
    return (
        Path(_native_python()).exists()
        and shutil.which("bash") is not None
        and shutil.which("RNAfold") is not None
        and (CRISPRON_DIR / "bin" / "CRISPRon.sh").exists()
    )


def _resolve_mode(timeout_s: int = 30) -> str | None:
    """返回实际可用的执行模式 'wsl'/'native'，不可用返回 None。"""
    m = _mode()
    if m == "wsl":
        return "wsl" if _wsl_ready(timeout_s) else None
    if m == "native":
        return "native" if _native_ready() else None
    # auto：Windows 优先 wsl（行为不变），否则 native
    if shutil.which("wsl") is not None and _wsl_ready(timeout_s):
        return "wsl"
    if _native_ready():
        return "native"
    return None


def _to_wsl(path) -> str:
    """Windows 绝对路径 → WSL 自动挂载路径（D:\\a\\b → /mnt/d/a/b）。"""
    p = str(Path(path).resolve()).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def is_available(timeout_s: int = 30) -> bool:
    """真实 CRISPRon 管线是否可用。只做一次性探测，不实跑打分。"""
    return _resolve_mode(timeout_s) is not None


def score(seq30_list, timeout_s: int = DEFAULT_TIMEOUT_S, chunk_size: int = CHUNK_SIZE) -> dict:
    """对 seq30 列表实跑 CRISPRon，返回 {seq30: 分数}。

    内部按 chunk_size 分块调用：单次 WSL 载荷被限定在历史验证过的规模内
    （训练集批量口径为 1361 条），避免大批量调用方（如 demo/prepare_demo_data.py
    的 batch_size=5000）把未经验证的规模一次性压给 CRISPRon。
    某块失败只影响该块（其序列由调用方降级并标注），其余块照常返回。
    整体不可用时返回 {}；**本函数绝不返回近似值冒充真实值**。
    """
    seqs = [str(s).upper().strip() for s in seq30_list]
    if not seqs or not is_available():
        return {}
    out = {}
    for i in range(0, len(seqs), chunk_size):
        out.update(_score_chunk(seqs[i:i + chunk_size], timeout_s))
    return out


def _run_wsl(in_fa: Path, out_dir: Path, timeout_s: int) -> bool:
    # 路径必须 shell 引用：交付包解压目录常含中文/空格/全角括号（如「XXX+参赛代码（区赛）」），
    # 未引用的 `cd <path>` 会被 word splitting 截断 -> CRISPRon 静默失败 -> 全量降级为近似式。
    cmd = (f"{_ACTIVATE} && cd {shlex.quote(_to_wsl(CRISPRON_DIR))} && "
           f"bash bin/CRISPRon.sh {shlex.quote(_to_wsl(in_fa))} {shlex.quote(_to_wsl(out_dir))}")
    try:
        r = subprocess.run(["wsl", "-d", WSL_DISTRO, "bash", "-lc", cmd],
                           capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _run_native(in_fa: Path, out_dir: Path, timeout_s: int) -> bool:
    env = os.environ.copy()
    # CRISPRon.sh 内脚本 shebang 为 `#!/usr/bin/env python3`，
    # 必须让 PATH 解析到 TF2.14 环境（CRISPRON_PYTHON 所在目录前置）。
    env["PATH"] = str(Path(_native_python()).parent) + os.pathsep + env.get("PATH", "")
    cmd = ["bash", str(CRISPRON_DIR / "bin" / "CRISPRon.sh"), str(in_fa), str(out_dir)]
    try:
        r = subprocess.run(cmd, cwd=str(CRISPRON_DIR), env=env,
                           capture_output=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _score_chunk(seqs, timeout_s: int) -> dict:
    """单块实跑；任何失败返回 {}（不抛异常）。"""
    mode = _resolve_mode()
    if mode is None:
        return {}
    work = Path(tempfile.mkdtemp(prefix="crispron_"))
    try:
        in_fa = work / "in.fa"
        out_dir = work / "out"
        keys = [f"g{i:05d}" for i in range(len(seqs))]
        with open(in_fa, "w", encoding="ascii") as fh:
            for k, s in zip(keys, seqs):
                fh.write(f">{k}\n{s}\n")

        if mode == "wsl":
            ok = _run_wsl(in_fa, out_dir, timeout_s)
        else:
            ok = _run_native(in_fa, out_dir, timeout_s)
        if not ok:
            return {}

        csv_path = out_dir / "crispron.csv"
        if not csv_path.exists():
            return {}
        res = pd.read_csv(csv_path)
        if not {"ID", "30mer", "CRISPRon"}.issubset(res.columns) or res.empty:
            return {}

        res["key"] = res["ID"].astype(str).str.replace(r"_[pm]_[0-9]+$", "", regex=True)
        res["seq30"] = res["key"].map(dict(zip(keys, seqs)))
        res = res[res["30mer"] == res["seq30"]]
        return {s: float(v) for s, v in zip(res["seq30"], res["CRISPRon"])}
    finally:
        shutil.rmtree(work, ignore_errors=True)
