# -*- coding: utf-8 -*-
"""sequence_spec.py — 靶位点 30bp 序列规格、解构与物理特征单一来源。

契约定义：
    Target Site (seq30, 30bp):
    [0:4]   5' Flank (4nt 上游)
    [4:24]  Guide (20nt 引导序列)
    [18:24] Seed (6nt 种子区，Guide 紧邻 PAM 的第 15–20 位)
    [24:27] PAM (3nt，须为 NGG，即 [25:27] 为 GG)
    [24:25] PAM N 碱基 (进行 A/C/G/T One-Hot 编码)
    [27:30] 3' Flank (3nt 下游)
"""
from __future__ import annotations

import re
from typing import NamedTuple

# 切片常量单点定义
FLANK_5P_SLICE = slice(0, 4)
GUIDE_SLICE = slice(4, 24)
SEED_SLICE = slice(18, 24)
PAM_SLICE = slice(24, 27)
PAM_N_SLICE = slice(24, 25)
FLANK_3P_SLICE = slice(27, 30)

SEQ30_PATTERN = re.compile(r"^[ACGT]{30}$")

# 9 个序列派生特征（10 维标准特征中除去 deepspcas9_score / crispron_score 两个模型分）。
# 列名与顺序即模型输入语义，由本模块单点定义；features_common.seq_features 是其向量化适配器。
PAM_ONEHOT = ["pam_n_A", "pam_n_C", "pam_n_G", "pam_n_T"]
SEQ_FEATURE_COLS = ["gc_total", "gc_seed", "tm", "poly_t"] + PAM_ONEHOT

# 尝试导入 Bio.SeqUtils，环境缺失时平滑降级（如 demo 环境无 Bio）
try:
    from Bio.SeqUtils import gc_fraction as _bio_gc_fraction
    from Bio.SeqUtils.MeltingTemp import Tm_NN as _bio_tm_nn
    _HAS_BIO = True
except ImportError:
    _HAS_BIO = False


def validate_seq30(seq: str) -> str | None:
    """验证 30bp 序列合法性。
    
    返回 None 表示合法；非法时返回中文错误原因。
    布局：4nt 上游 + 20nt guide + NGG PAM + 3nt 下游。
    """
    if not isinstance(seq, str):
        return "输入必须为字符串"
    s = seq.strip().upper()
    if len(s) != 30:
        return f"长度为 {len(s)}，须为 30bp"
    if not SEQ30_PATTERN.match(s):
        return "含非法字符，仅允许 A/C/G/T"
    if s[25:27] != "GG":
        return "第 25–27 位须为 NGG PAM（即第 26、27 位为 GG）"
    return None


def calc_gc(seq: str) -> float:
    """计算序列 GC 比例 [0.0, 1.0]。"""
    if _HAS_BIO:
        return float(_bio_gc_fraction(seq))
    if not seq:
        return 0.0
    s = seq.upper()
    return sum(1 for b in s if b in "GC") / float(len(s))


# SantaLucia 1998 经典近邻热力学参数表（当无 Biopython 时的等价纯 Python 降级）
_NN_TABLE = {
    "AA": (-7.9, -22.2), "TT": (-7.9, -22.2),
    "AT": (-7.2, -20.4), "TA": (-7.2, -21.3),
    "CA": (-8.5, -22.7), "TG": (-8.5, -22.7),
    "GT": (-8.4, -22.4), "AC": (-8.4, -22.4),
    "CT": (-7.8, -21.0), "AG": (-7.8, -21.0),
    "GA": (-8.2, -22.2), "TC": (-8.2, -22.2),
    "CG": (-10.6, -27.2), "GC": (-9.8, -24.4),
    "GG": (-8.0, -19.9), "CC": (-8.0, -19.9),
}


def calc_tm(seq: str) -> float:
    """计算 20nt 序列的退火熔解温度 Tm (°C)。
    
    优先调用 Biopython Tm_NN；若未安装 Biopython，调用 SantaLucia 1998 近邻公式。
    """
    if _HAS_BIO:
        return float(_bio_tm_nn(seq))
    
    # 纯 Python 近邻计算（1M 盐浓度，50nM 引物浓度近似）
    s = seq.upper()
    if len(s) < 2:
        return 0.0
    dh = 0.0
    ds = 0.0
    # 端点修正
    init_gc = sum(1 for b in (s[0], s[-1]) if b in "GC")
    init_at = 2 - init_gc
    dh += 0.1 * init_gc + 2.3 * init_at
    ds += -2.8 * init_gc + 4.1 * init_at
    for i in range(len(s) - 1):
        pair = s[i:i+2]
        h, s_entropy = _NN_TABLE.get(pair, (-8.0, -22.0))
        dh += h
        ds += s_entropy
    # Tm = (1000 * dH) / (dS + R * ln(c/4)) - 273.15, R=1.9872
    r_ln_c = 1.9872 * (-15.4249) # 50nM
    tm_kelvin = (1000.0 * dh) / (ds + r_ln_c)
    return float(tm_kelvin - 273.15)


def seq_feature_dict(seq30: str) -> dict:
    """seq30 → 9 个序列派生特征（SEQ_FEATURE_COLS 的取值语义单点定义）。

    不做校验——校验是 validate_seq30 的职责；本函数只管特征语义：
    gc_total=guide GC、gc_seed=种子区 GC、tm=guide Tm、poly_t=guide 含 TTTT、
    pam_n_* = PAM 首碱基 one-hot。SequenceSpec 的特征属性与
    features_common.seq_features（向量化适配器）都从这里取定义，训练与推理不得分家。
    """
    s = str(seq30).upper()
    guide = s[GUIDE_SLICE]
    out = {
        "gc_total": calc_gc(guide),
        "gc_seed": calc_gc(s[SEED_SLICE]),
        "tm": calc_tm(guide),
        "poly_t": 1 if "TTTT" in guide else 0,
    }
    pam_n = s[PAM_N_SLICE]
    for b in "ACGT":
        out[f"pam_n_{b}"] = 1.0 if pam_n == b else 0.0
    return out


class SequenceSpec:
    """30bp 靶位点序列领域值对象。"""

    __slots__ = ("_raw", "_seq30", "_guide", "_seed", "_pam", "_pam_n", "_flank_5p", "_flank_3p", "_feat")

    def __init__(self, seq30: str):
        err = validate_seq30(seq30)
        if err is not None:
            raise ValueError(f"无效靶位点序列 {seq30!r}: {err}")
        self._raw = seq30
        self._seq30 = seq30.strip().upper()
        self._flank_5p = self._seq30[FLANK_5P_SLICE]
        self._guide = self._seq30[GUIDE_SLICE]
        self._seed = self._seq30[SEED_SLICE]
        self._pam = self._seq30[PAM_SLICE]
        self._pam_n = self._seq30[PAM_N_SLICE]
        self._flank_3p = self._seq30[FLANK_3P_SLICE]
        self._feat = seq_feature_dict(self._seq30)

    @classmethod
    def parse(cls, seq: str) -> SequenceSpec:
        return cls(seq)

    @classmethod
    def try_parse(cls, seq: str) -> tuple[SequenceSpec | None, str | None]:
        err = validate_seq30(seq)
        if err is not None:
            return None, err
        return cls(seq), None

    @property
    def seq30(self) -> str:
        return self._seq30

    @property
    def guide(self) -> str:
        return self._guide

    @property
    def seed(self) -> str:
        return self._seed

    @property
    def pam(self) -> str:
        return self._pam

    @property
    def pam_n(self) -> str:
        return self._pam_n

    @property
    def flank_5p(self) -> str:
        return self._flank_5p

    @property
    def flank_3p(self) -> str:
        return self._flank_3p

    @property
    def gc_total(self) -> float:
        return self._feat["gc_total"]

    @property
    def gc_seed(self) -> float:
        return self._feat["gc_seed"]

    @property
    def tm(self) -> float:
        return self._feat["tm"]

    @property
    def poly_t(self) -> int:
        return self._feat["poly_t"]

    @property
    def pam_onehot(self) -> dict[str, float]:
        return {k: self._feat[k] for k in PAM_ONEHOT}

    def __repr__(self) -> str:
        return f"SequenceSpec({self._seq30[0:4]}-{self._guide}-{self._pam}-{self._seq30[27:30]})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SequenceSpec):
            return self._seq30 == other._seq30
        return False

    def __hash__(self) -> int:
        return hash(self._seq30)
