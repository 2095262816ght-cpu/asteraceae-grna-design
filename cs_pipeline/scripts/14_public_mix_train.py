# -*- coding: utf-8 -*-
"""14: 公开数据加权混合训练（详案预案落地，division_plan_cs.md A5「公开数据加权混合预案」）。

数据源：data/raw/public_datasets/Luo2020_Kim2019.xlsx（23,902 条 30mer，
= DeepSpCas9 训练集 Kim2019 12,784+526 + CRISPRon 训练集 Luo2020 10,543+，标签 indel%）。

详案既定纪律：
  - 公开数据只进训练，【评估永远只用自有橡胶草数据】（外层测试折 + LOGO-CV 同 13）；
  - 标签折算：公开标签按 rank(pct=True)*100 归一到同尺度；
  - 权重：自有 50 : 公开 1；
  - alpha 仍只在自有训练折内用 GroupKFold 调（与 13 相同）。

分步运行（crispr 环境，cs_pipeline/ 下）：
    python scripts/14_public_mix_train.py prep    # 校验+导出公开数据 fasta/csv
    python scripts/14_public_mix_train.py deep    # DeepSpCas9 打分（后台）
    python scripts/14_public_mix_train.py crisp   # CRISPRon 打分（WSL，后台）
    python scripts/14_public_mix_train.py train   # 特征组装 + 混合训练 + 评估
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from core.sequence_spec import seq_feature_dict  # noqa: E402
XLSX = BASE / "data" / "raw" / "public_datasets" / "Luo2020_Kim2019.xlsx"
PUB_CSV = BASE / "data" / "hitom" / "public_luo2020_kim2019_clean.csv"
IO = BASE / "data" / "hitom" / "crispron_io"
DEEP_OUT = BASE / "results" / "public_score_deep_0917.csv"
CRISP_OUT = BASE / "results" / "public_score_crisp_0917.csv"
FEAT_OUT = BASE / "results" / "public_features_0917.csv"
OWN_FM = BASE / "results" / "feature_matrix_full_0916.csv"
RESULT_OUT = BASE / "results" / "model_comparison_mixed_0917.csv"
LOGO_OUT = BASE / "results" / "logo_cv_mixed_0917.csv"
MODEL_OUT = BASE / "results" / "meta_model_ridge_mixed_0917.joblib"

FEATS = ["deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
         "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_T"]
OWN_WEIGHT = 50.0
PUB_WEIGHT = 1.0


def stage_prep():
    df = pd.read_excel(XLSX, sheet_name="Luo2020_Kim2019")
    df = df[["Dataset", "30mer_gRNA", "Indel_freq_HEK293T"]].copy()
    df.columns = ["dataset", "seq30", "indel_freq"]
    df["seq30"] = df["seq30"].str.upper().str.strip()
    assert df["seq30"].str.fullmatch(r"[ACGT]{30}").all(), "存在非法 30mer"
    assert df["indel_freq"].notna().all()
    df = df.drop_duplicates("seq30").reset_index(drop=True)
    df.insert(0, "pub_id", [f"pub_{i:06d}" for i in range(len(df))])
    df.to_csv(PUB_CSV, index=False)
    print(f"OK: {len(df)} 条（去重后）-> {PUB_CSV}")
    print(df["dataset"].value_counts().to_string())
    print(f"标签范围: {df['indel_freq'].min():.2f} ~ {df['indel_freq'].max():.2f}")


def _load_pub():
    return pd.read_csv(PUB_CSV)


def stage_deep():
    from genet.predict import SpCas9
    df = _load_pub()
    pred = SpCas9().predict(df.seq30.tolist())
    assert (pred["Target"].values == df.seq30.values).all()
    out = pd.DataFrame({"pub_id": df.pub_id, "deepspcas9_score": pred["SpCas9"].values})
    assert out["deepspcas9_score"].notna().all()
    out.to_csv(DEEP_OUT, index=False)
    print(f"OK: {len(out)} -> {DEEP_OUT}")


def stage_crisp():
    df = _load_pub()
    IO.mkdir(parents=True, exist_ok=True)
    with open(IO / "seq30_in.fa", "w") as f:
        for _, r in df.iterrows():
            f.write(f">{r.pub_id}\n{r.seq30}\n")
    subprocess.run(["wsl", "-d", "Ubuntu-22.04", "bash",
                    "/mnt/d/lifesciencechallenge/cs_pipeline/env/run_crispron_wsl.sh"], check=True)
    res = pd.read_csv(IO / "out" / "crispron.csv")
    res["pub_id"] = res["ID"].str.replace(r"_[pm]_[0-9]+$", "", regex=True)
    res = res.merge(df[["pub_id", "seq30"]], on="pub_id")
    res = res[res["30mer"] == res["seq30"]]
    out = res[["pub_id", "CRISPRon"]].rename(columns={"CRISPRon": "crispron_score"})
    assert len(out) == len(df), f"行数不符: {len(out)} vs {len(df)}"
    out.to_csv(CRISP_OUT, index=False)
    print(f"OK: {len(out)} -> {CRISP_OUT}")


def _build_pub_features():
    df = _load_pub()
    deep = pd.read_csv(DEEP_OUT)
    crisp = pd.read_csv(CRISP_OUT)
    df = df.merge(deep, on="pub_id", validate="1:1").merge(crisp, on="pub_id", validate="1:1")
    # 特征语义单点定义在 core.sequence_spec；只取本模型 FEATS 用到的列，输出 schema 不变
    seqf = pd.DataFrame.from_records(
        [seq_feature_dict(s) for s in df["seq30"]], index=df.index
    )
    for c in ("gc_total", "gc_seed", "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_T"):
        df[c] = seqf[c]
    df["y_pub"] = df["indel_freq"].rank(pct=True) * 100
    assert not df[FEATS + ["y_pub"]].isna().any().any()
    df.to_csv(FEAT_OUT, index=False)
    return df


def stage_train():
    import joblib
    from scipy.stats import spearmanr
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

    pub = _build_pub_features()
    X_pub, y_pub = pub[FEATS].astype(float).values, pub["y_pub"].values
    w_pub = np.full(len(pub), PUB_WEIGHT)
    print(f"公开数据: {len(pub)} 条")

    # 动物基准对照（详案 A5：同管线在公开数据上的表现，供报告三段曲线）
    rho_deep_pub, _ = spearmanr(pub["deepspcas9_score"], pub["indel_freq"])
    rho_crisp_pub, _ = spearmanr(pub["crispron_score"], pub["indel_freq"])
    print(f"动物基准（in-sample 上限，文献 oos≈0.5）: DeepSpCas9 ρ={rho_deep_pub:.3f}, CRISPRon ρ={rho_crisp_pub:.3f}")

    own = pd.read_csv(OWN_FM)
    HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
               "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}
    own["gene_group"] = own["gene_id"].replace(HOMOLOG)
    X_own = own[FEATS].astype(float).values
    y_own = own["efficiency_norm"].astype(float).values
    groups = own["gene_group"].values

    def fit_mixed(X_tr, y_tr, w_own_tr, alpha):
        X_all = np.vstack([X_tr, X_pub])
        y_all = np.concatenate([y_tr, y_pub])
        w_all = np.concatenate([w_own_tr, w_pub])
        return Ridge(alpha=alpha, solver="svd").fit(X_all, y_all, sample_weight=w_all)

    def grid_alpha(X_tr, y_tr, g_tr):
        cv = list(GroupKFold(min(5, len(set(g_tr)))).split(X_tr, y_tr, g_tr))
        gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)},
                          cv=cv, scoring="neg_mean_squared_error")
        gs.fit(X_tr, y_tr)
        return gs.best_params_["alpha"]

    # ---- 外层测试折（与 13 同一划分，rs=42）----
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    tr, te = next(gss.split(X_own, y_own, groups))
    alpha = grid_alpha(X_own[tr], y_own[tr], groups[tr])
    m = fit_mixed(X_own[tr], y_own[tr], np.full(len(tr), OWN_WEIGHT), alpha)
    rho_te, _ = spearmanr(m.predict(X_own[te]), y_own[te])
    print(f"\n[外层测试折] alpha={alpha:.2f}  混合模型 ρ={rho_te:.4f}（对照：13 自有-only 为 -0.6761）")

    # ---- LOGO-CV（评估只用自有数据）----
    logo = LeaveOneGroupOut()
    rows = []
    for tr_i, te_i in logo.split(X_own, y_own, groups):
        a_i = grid_alpha(X_own[tr_i], y_own[tr_i], groups[tr_i])
        m_i = fit_mixed(X_own[tr_i], y_own[tr_i], np.full(len(tr_i), OWN_WEIGHT), a_i)
        pred_i = m_i.predict(X_own[te_i])
        rho_i = spearmanr(pred_i, y_own[te_i])[0] if len(set(y_own[te_i])) > 1 else np.nan
        rows.append({"held_out_gene": groups[te_i][0], "n_samples": len(te_i), "rho": rho_i})
    logo_df = pd.DataFrame(rows)
    logo_df.to_csv(LOGO_OUT, index=False)
    med = logo_df["rho"].dropna().median()
    print(f"\n[LOGO-CV] 混合模型中位 ρ={med:.4f}（对照：自有-only 0.4140，旧冻结 -0.2254）")
    print(logo_df.to_string(index=False))

    # ---- 全量拟合存档 + guide 级 sanity ----
    alpha_full = grid_alpha(X_own, y_own, groups)
    m_full = fit_mixed(X_own, y_own, np.full(len(own), OWN_WEIGHT), alpha_full)
    joblib.dump(m_full, MODEL_OUT)
    g = own.assign(pred=np.clip(m_full.predict(X_own), 0, 100)).groupby("seq20").agg(
        y_mean=("efficiency_norm", "mean"), pred=("pred", "mean"))
    rho_guide, _ = spearmanr(g.y_mean, g.pred)
    print(f"\n[guide 级 sanity] 混合模型 ρ={rho_guide:.3f}（自有-only 为 0.402）")

    comp = pd.DataFrame([
        {"model": "Stacking 自有-only（13）", "rho_test": -0.6761, "rho_logo_cv_median": 0.4140},
        {"model": "Stacking 公开混合（详案预案）", "rho_test": round(rho_te, 4), "rho_logo_cv_median": round(med, 4)},
        {"model": "动物基准 DeepSpCas9（公开集 in-sample）", "rho_test": np.nan, "rho_logo_cv_median": round(rho_deep_pub, 4)},
        {"model": "动物基准 CRISPRon（公开集 in-sample）", "rho_test": np.nan, "rho_logo_cv_median": round(rho_crisp_pub, 4)},
    ])
    comp.to_csv(RESULT_OUT, index=False)
    print(f"\nSaved {RESULT_OUT}, {LOGO_OUT}, {MODEL_OUT}")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    {"prep": stage_prep, "deep": stage_deep, "crisp": stage_crisp, "train": stage_train}.get(
        stage, lambda: sys.exit("用法: 14_public_mix_train.py [prep|deep|crisp|train]"))()
