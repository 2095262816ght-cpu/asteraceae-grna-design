"""计A → 计B 的模型官方推理接口（2026-09-21 升级为 v2.1 终版形态二模型），约定见《分工详案_计算机系》（docs/plans/division_plan_cs.md）0.4 节。

计B 只调 predict_efficiency()，不接触模型内部细节；
默认加载模型：results/meta_model_hier_bb_nob879_0921.joblib（基于 noB879 纯A级金标准训练的分层选择性 Beta-Binomial GLMM）。
打分定位：用于同一基因内候选 guide 的【相对活性排序与择优推荐】（非绝对 indel% 承诺）。
CRISPRon 说明：交互推理与离线批量打分现均经 WSL 原生工具实跑（scripts/crispron_wsl.py，
与 scripts/03_score_crispron.py 同一管线、同一取值约定）。WSL 不可用或该条无精确 30mer
匹配时退回经验近似式，并在返回的 crispron_source 列逐条标注 approximated，调用方须向用户
明示——此前该近似式被静默当作真实特征使用（P0「推理期特征伪造」），实测对 demo 输入框
预填的 placeholder 序列偏 +8.66 分 / 相对 14.5%。
"""


import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from genet.predict import SpCas9

BASE = Path(__file__).resolve().parent.parent
# 本模块既可能以 `python scripts/predict.py` 直接运行（此时 sys.path[0] = scripts/），
# 也可能被 app/score_deepspcas9_cli.py 以 `from scripts.predict import ...` 导入
# （此时 sys.path[0] = cs_pipeline/）。两种情形都要能取到同目录的 features_common。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from crispron_scorer import CrispronScorer
from features_common import FEATURE_COLS, seq_features
# 2026-09-21 架构决议升级：默认加载 noB879 纯A级金标准 + 形态二 (分层选择性 Beta-Binomial GLMM) 生产模型
MODEL_PATH = BASE / "results" / "meta_model_hier_bb_nob879_0921.joblib"
LEGACY_MODEL_PATH = BASE / "results" / "meta_model_ridge_full_0916.joblib"

OUT_COLS = ["seq30", "deepspcas9_score", "crispron_score", "crispron_source", "stacking_score"]

_meta_model = None


def _get_meta_model():
    global _meta_model
    if _meta_model is None:
        target_path = MODEL_PATH if MODEL_PATH.exists() else LEGACY_MODEL_PATH
        if not target_path.exists():
            raise FileNotFoundError(f"Stacking/GLMM 模型权重未就绪: {target_path}")
        _meta_model = joblib.load(target_path)
    return _meta_model


def predict_details(seq30_list: list[str]) -> pd.DataFrame:
    """输入30bp序列列表，返回 seq30, deepspcas9_score, crispron_score, crispron_source,
    stacking_score 的 DataFrame。

    crispron_source 逐条标明该维特征来源：`wsl_real` = 经 WSL 实跑真实 CRISPRon
    （与训练集同管线同约定）；`approximated` = 管线不可用时的经验近似式降级值。
    调用方（含 demo Tab2）必须把该标记透出给用户，不得把降级值当真实模型输出展示。
    """
    if not seq30_list:
        return pd.DataFrame(columns=OUT_COLS)

    meta = _get_meta_model()
    tf.compat.v1.reset_default_graph()
    spcas9 = SpCas9()

    seqs = []
    for s in seq30_list:
        s = s.upper().strip()
        assert len(s) == 30, f"序列长度必须为 30bp，输入为 {len(s)}bp: {s}"
        seqs.append(s)

    # 9 个序列派生特征由 features_common.seq_features 单点定义，与训练路径同源
    feat_df = seq_features(pd.Series(seqs))
    feat_df.insert(0, "seq30", seqs)

    # 1. DeepSpCas9 预测
    pred_deep = spcas9.predict(seq30_list)
    feat_df["deepspcas9_score"] = pred_deep["SpCas9"].values.round(4)

    # 2. CRISPRon：来源裁决统一由 CrispronScorer 承担（真实模型优先、逐条降级并标注
    #    crispron_source）—— 绝不静默用近似值冒充真实值。
    scored = CrispronScorer().score(seqs, feat_df["deepspcas9_score"], feat_df["tm"])
    feat_df["crispron_score"] = scored["crispron_score"]
    feat_df["crispron_source"] = scored["crispron_source"]

    # 3. 推理逻辑自适应
    if isinstance(meta, dict) and "beta" in meta:
        # 形态二：分层 Beta-Binomial GLMM 纯序列生物学活性推断。
        # 权重里记录的 feature_cols 必须与 features_common 的单点定义逐位一致，
        # 否则训练与推理就在用不同的特征，而且不会有任何报错。
        feats = list(meta.get("feature_cols", FEATURE_COLS))
        assert feats == FEATURE_COLS, \
            f"模型 feature_cols 与 features_common.FEATURE_COLS 不一致：{feats}"
        X = feat_df[feats].astype(float).values
        Z = (X - meta["mu"]) / meta["std"]
        logits = meta["beta0"] + np.dot(Z, meta["beta"])
        probs = 1.0 / (1.0 + np.exp(-logits))
        feat_df["stacking_score"] = np.clip(probs * 100.0, 0.0, 100.0).round(2)
    else:
        # 兼容旧版 scikit-learn Ridge 模型
        feats = [
            "deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
            "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_T",
        ]
        X = feat_df[feats].astype(float).values
        preds = meta.predict(X)
        feat_df["stacking_score"] = np.clip(preds, 0.0, 100.0).round(2)

    return feat_df[OUT_COLS]


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

