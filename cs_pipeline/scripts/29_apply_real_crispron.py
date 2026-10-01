"""29: 合并真实 CRISPRon 真值 → 重算 efficiency_score → 重建 Top100（方案 3 收尾）。

输入：
- results/real_crispron_top100_0927.csv（scripts/28 产物，seq30→真实 CRISPRon 分）
- results/lettuce_all_genes_top100_candidates.csv（脚本 26/27 产物，crispron 为近似值）
- results/meta_model_hier_bb_nob879_0921.joblib（形态二 GLMM）

处理：
1. Top100 行按 seq30 回填真实 crispron_score，crispron_source 改为 wsl_real
   （个别打分失败序列保留近似值与 approximated 标注，不冒充真值）；
2. 用形态二 GLMM 公式重算 efficiency_score（与 scripts/26 同一 FEATURE_COLS 口径）；
3. 按基因内新 efficiency_score 重排 Top100（成员不变——方案 3 只对进库 Top100 跑真值，
   库外 900 余万条仍是近似分，不参与重选）；
4. 旧 top100 备份到 results/backup/，--parts 时同步更新 scored_genome 分片对应行。

输出统计：新旧 efficiency 排名 Spearman、Top10 翻转率，作为近似式影响的量化记录。

运行（cs_pipeline/ 下，需要 joblib/genet 环境即 crispr conda env）：
    python scripts/29_apply_real_crispron.py            # 只更新 top100 + 统计
    python scripts/29_apply_real_crispron.py --parts    # 同步更新 scored_genome 分片
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from scripts.features_common import FEATURE_COLS, seq_features  # noqa: E402
from scripts.crispron_scorer import SOURCE_WSL_REAL  # noqa: E402

REAL_CSV = BASE / "results" / "real_crispron_top100_0927.csv"
TOP_CSV = BASE / "results" / "lettuce_all_genes_top100_candidates.csv"
MODEL_PATH = BASE / "results" / "meta_model_hier_bb_nob879_0921.joblib"
BACKUP_DIR = BASE / "results" / "backup"
PARTS_DIR = BASE / "results" / "scored_genome"


def glmm_efficiency(df: pd.DataFrame, meta: dict) -> np.ndarray:
    X = df[FEATURE_COLS].astype(float).values
    Z = (X - meta["mu"]) / meta["std"]
    logits = meta["beta0"] + np.dot(Z, meta["beta"])
    probs = 1.0 / (1.0 + np.exp(-logits))
    return np.clip(probs * 100.0, 0.0, 100.0).round(2)


def rank_corr(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", action="store_true", help="同步更新 scored_genome 分片")
    args = ap.parse_args()

    t0 = time.time()
    real = pd.read_csv(REAL_CSV)
    real_map = real.drop_duplicates("seq30").set_index("seq30")["crispron_score"]
    print(f"真实 CRISPRon {len(real_map)} 条唯一序列", flush=True)

    df = pd.read_csv(TOP_CSV)
    print(f"Top100 读入 {len(df)} 行", flush=True)

    old_eff = df["efficiency_score"].to_numpy(dtype=float)
    is_real = df["seq30"].astype(str).isin(real_map.index)
    n_real = int(is_real.sum())
    len_df = len(df)
    print(f"可回填真值 {n_real} / {len_df}（{(n_real / len_df * 100):.2f}%）", flush=True)

    df.loc[is_real, "crispron_score"] = df.loc[is_real, "seq30"].map(real_map)
    df.loc[is_real, "crispron_source"] = SOURCE_WSL_REAL

    meta = joblib.load(MODEL_PATH)
    feat = seq_features(df["seq30"].astype(str))
    for c in feat.columns:
        df[c] = feat[c].values
    df["efficiency_score"] = glmm_efficiency(df, meta)
    new_eff = df["efficiency_score"].to_numpy(dtype=float)

    rho = rank_corr(old_eff, new_eff)
    print(f"新旧 efficiency 排名 Spearman = {rho:.4f}", flush=True)

    top10_old = df.assign(_old=old_eff).sort_values(["gene_id", "_old"], ascending=[True, False]) \
        .groupby("gene_id", sort=False).head(10).groupby("gene_id")["guide_id"].apply(set)
    top10_new = df.sort_values(["gene_id", "efficiency_score"], ascending=[True, False]) \
        .groupby("gene_id", sort=False).head(10).groupby("gene_id")["guide_id"].apply(set)
    swaps = [1 - len(o & n) / 10 for o, n in zip(top10_old, top10_new)]
    print(f"Top10 平均翻转率 = {np.mean(swaps) * 100:.1f}%（0%=完全不变）", flush=True)

    # 基因内重排（成员不变），并更新展示列
    df = (
        df.sort_values(["gene_id", "efficiency_score"], ascending=[True, False])
        .groupby("gene_id", sort=False)
        .head(100)
    )
    BACKUP_DIR.mkdir(exist_ok=True)
    backup = BACKUP_DIR / f"{TOP_CSV.stem}_approx_0927{TOP_CSV.suffix}"
    if not backup.exists():
        shutil.copy2(TOP_CSV, backup)
        print(f"旧 Top100 已备份：{backup}", flush=True)
    df.to_csv(TOP_CSV, index=False)
    print(f"新 Top100 已写出：{TOP_CSV}（{len(df)} 行）", flush=True)

    if args.parts:
        guide_ids = set(df["guide_id"].astype(str))
        real_guide = df.set_index("guide_id")[["crispron_score", "efficiency_score", "crispron_source"]]
        parts = sorted(PARTS_DIR.glob("part_*.csv"))
        for i, p in enumerate(parts):
            d = pd.read_csv(p)
            hit = d["guide_id"].astype(str).isin(guide_ids)
            if hit.any():
                d.loc[hit, "crispron_score"] = d.loc[hit, "guide_id"].map(real_guide["crispron_score"])
                d.loc[hit, "efficiency_score"] = d.loc[hit, "guide_id"].map(real_guide["efficiency_score"])
                d.loc[hit, "crispron_source"] = SOURCE_WSL_REAL
                d.to_csv(p, index=False)
            if (i + 1) % 50 == 0:
                print(f"分片更新 {i + 1}/{len(parts)}", flush=True)
        print("scored_genome 分片同步完成", flush=True)

    print(f"总耗时 {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
