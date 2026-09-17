# -*- coding: utf-8 -*-
"""demo 候选全量重打分（2026-09-16）：真实 DeepSpCas9 + 真实 CRISPRon + 全量训练 Stacking 模型。

背景：demo/app_data.csv 的 efficiency_score 由旧模型（LOGO-CV ρ=-0.225）产出，
且 predict.py 在推理时用近似公式伪造 crispron 特征（CHANGELOG_0927 已标注不可信）。
本脚本对 19,839 条 demo 候选改用真实双模型打分 + meta_model_ridge_full_0916.joblib，
产出新列 efficiency_score_full_0916（不动旧列）。

分三步（crispr 环境运行，在 cs_pipeline/ 下）：
    python demo/rescore_demo_full_0916.py deep      # DeepSpCas9 打分（本地 TF）
    python demo/rescore_demo_full_0916.py crisp     # CRISPRon 打分（WSL）
    python demo/rescore_demo_full_0916.py assemble  # 特征组装 + 元模型预测 + 写回 app_data.csv
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent          # cs_pipeline/
APP_DATA = BASE / "demo" / "app_data.csv"
DEEP_OUT = BASE / "results" / "demo_score_deep_full_0916.csv"
CRISP_OUT = BASE / "results" / "demo_score_crisp_full_0916.csv"
MODEL = BASE / "results" / "meta_model_ridge_full_0916.joblib"
IO = BASE / "data" / "hitom" / "crispron_io"


def load_candidates():
    df = pd.read_csv(APP_DATA, dtype={"seq20": "string", "seq30": "string", "pam": "string"})
    assert df["seq30"].str.fullmatch(r"[ACGT]{30}").all(), "app_data.csv 存在非法 seq30"
    return df


def stage_deep():
    from genet.predict import SpCas9
    df = load_candidates()
    pred = SpCas9().predict(df.seq30.tolist())
    assert (pred["Target"].values == df.seq30.values).all()
    out = pd.DataFrame({"guide_id": df.guide_id, "deepspcas9_score": pred["SpCas9"].values})
    assert out["deepspcas9_score"].notna().all()
    out.to_csv(DEEP_OUT, index=False)
    print(f"OK: {len(out)} -> {DEEP_OUT}")


def stage_crisp():
    df = load_candidates()
    IO.mkdir(parents=True, exist_ok=True)
    with open(IO / "seq30_in.fa", "w") as f:
        for _, r in df.iterrows():
            f.write(f">{r.guide_id}\n{r.seq30}\n")
    subprocess.run(["wsl", "-d", "Ubuntu-22.04", "bash",
                    "/mnt/d/lifesciencechallenge/cs_pipeline/env/run_crispron_wsl.sh"], check=True)
    res = pd.read_csv(IO / "out" / "crispron.csv")
    res["guide_id"] = res["ID"].str.replace(r"_[pm]_[0-9]+$", "", regex=True)
    res = res.merge(df[["guide_id", "seq30"]], on="guide_id")
    res = res[res["30mer"] == res["seq30"]]
    out = res[["guide_id", "CRISPRon"]].rename(columns={"CRISPRon": "crispron_score"})
    assert len(out) == len(df), f"行数不符: {len(out)} vs {len(df)}"
    out.to_csv(CRISP_OUT, index=False)
    print(f"OK: {len(out)} -> {CRISP_OUT}")


def stage_assemble():
    import joblib
    from Bio.SeqUtils import gc_fraction
    from Bio.SeqUtils.MeltingTemp import Tm_NN

    df = load_candidates()
    deep = pd.read_csv(DEEP_OUT)
    crisp = pd.read_csv(CRISP_OUT)
    df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")

    seq20 = df.seq30.str[4:24]
    feat = pd.DataFrame({
        "deepspcas9_score": df["deepspcas9_score"].astype(float),
        "crispron_score": df["crispron_score"].astype(float),
        "gc_total": seq20.map(gc_fraction),
        "gc_seed": df.seq30.str[18:24].map(gc_fraction),
        "tm": seq20.map(Tm_NN),
        "poly_t": seq20.str.contains("TTTT").astype(int),
        "pam_n_A": (df.seq30.str[24] == "A").astype(float),
        "pam_n_C": (df.seq30.str[24] == "C").astype(float),
        "pam_n_T": (df.seq30.str[24] == "T").astype(float),
    })
    FEATS = ["deepspcas9_score", "crispron_score", "gc_total", "gc_seed",
             "tm", "poly_t", "pam_n_A", "pam_n_C", "pam_n_T"]
    meta = joblib.load(MODEL)
    assert meta.n_features_in_ == len(FEATS)
    df["efficiency_score_full_0916"] = np.clip(meta.predict(feat[FEATS].values), 0, 100).round(2)

    bak = APP_DATA.with_suffix(".backup_20260916_pre_rescore.csv")
    if not bak.exists():
        pd.read_csv(APP_DATA).to_csv(bak, index=False)
        print(f"备份: {bak}")
    df.to_csv(APP_DATA, index=False)
    print(f"OK: {len(df)} 行写回 {APP_DATA}，新增列 efficiency_score_full_0916")
    print(df["efficiency_score_full_0916"].describe().round(2).to_string())


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    {"deep": stage_deep, "crisp": stage_crisp, "assemble": stage_assemble}.get(
        stage, lambda: sys.exit("用法: rescore_demo_full_0916.py [deep|crisp|assemble]"))()
