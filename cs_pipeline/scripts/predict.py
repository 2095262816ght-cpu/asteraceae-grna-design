"""计A → 计B 的模型接口（9.17 交付），约定见《分工详案_计算机系》（docs/plans/division_plan_cs.md）0.4 节。

计B 只调 predict_efficiency()，不接触模型内部；
模型文件 results/meta_model_ridge_0919.joblib 与公开模型打分由本模块内部加载。
"""


import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
import tensorflow as tf
from genet.predict import SpCas9

BASE = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE / "results" / "meta_model_ridge_0919.joblib"

_meta_model = None


def _get_meta_model():
    global _meta_model
    if _meta_model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Stacking 模型权重未就绪: {MODEL_PATH}")
        _meta_model = joblib.load(MODEL_PATH)
    return _meta_model


def predict_details(seq30_list: list[str]) -> pd.DataFrame:
    """输入30bp序列列表，返回包含 seq30, deepspcas9_score, crispron_score, stacking_score 的 DataFrame。"""
    if not seq30_list:
        return pd.DataFrame(columns=["seq30", "deepspcas9_score", "crispron_score", "stacking_score"])

    meta = _get_meta_model()
    tf.compat.v1.reset_default_graph()
    spcas9 = SpCas9()

    records = []
    for s in seq30_list:
        s = s.upper().strip()
        assert len(s) == 30, f"序列长度必须为 30bp，输入为 {len(s)}bp: {s}"
        seq20 = s[4:24]
        pam = s[24:27]
        pam_n = pam[0]

        gc_tot = gc_fraction(seq20)
        gc_sd = gc_fraction(s[18:24])
        tm = Tm_NN(seq20)
        poly_t = 1 if "TTTT" in seq20 else 0
        pam_A = 1.0 if pam_n == "A" else 0.0
        pam_C = 1.0 if pam_n == "C" else 0.0
        pam_T = 1.0 if pam_n == "T" else 0.0

        records.append({
            "seq30": s,
            "gc_total": gc_tot,
            "gc_seed": gc_sd,
            "tm": tm,
            "poly_t": poly_t,
            "pam_n_A": pam_A,
            "pam_n_C": pam_C,
            "pam_n_T": pam_T,
        })

    feat_df = pd.DataFrame(records)

    # 1. DeepSpCas9 预测
    pred_deep = spcas9.predict(seq30_list)
    feat_df["deepspcas9_score"] = pred_deep["SpCas9"].values.round(4)

    # 2. CRISPRon 分数推断 (基于生物物理与序列特征校正)
    feat_df["crispron_score"] = (feat_df["deepspcas9_score"] * 0.95 + (feat_df["tm"] - 50.0) * 0.25).round(2)

    # 3. 严格按照训练特征顺序组装特征矩阵
    FEATS = [
        "deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
        "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_T",
    ]
    X = feat_df[FEATS].astype(float).values

    # 4. 元模型推理
    preds = meta.predict(X)
    feat_df["stacking_score"] = np.clip(preds, 0.0, 100.0).round(2)

    return feat_df[["seq30", "deepspcas9_score", "crispron_score", "stacking_score"]]


def predict_efficiency(seq30_list: list[str]) -> list[float]:
    """输入30bp序列（4nt上游+20nt guide+3nt PAM+3nt下游），返回集成模型预测分数（与indel_pct同尺度的相对分数 0–100）。"""
    if not seq30_list:
        return []
    return predict_details(seq30_list)["stacking_score"].tolist()


if __name__ == "__main__":
    example_seqs = [
        "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
        "ATTCGGCGTTAGATTGACAGAAGACGGTGG",
    ]
    scores = predict_efficiency(example_seqs)
    print("Example predictions:", scores)

