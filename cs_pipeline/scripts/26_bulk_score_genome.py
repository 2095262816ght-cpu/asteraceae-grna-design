"""26: 全基因组候选批量打分（路径 C 预计算）。

输入：results/grna_candidates_lettuce_0923.csv（scripts/07 产物，约 1090 万条）
输出：results/scored_genome/part_XXXXXX.csv（分片，断点续跑，**永不删除**）
      results/scored_genome/scored_genome_manifest.json

打分口径（与 scripts/predict.py 形态二 GLMM 对齐，全量场景的降级约定）：
- deepspcas9_score：genet SpCas9 实跑
- crispron_score：经验近似式，crispron_source 固定为 approximated
  （全量 1e7 级别无法 WSL 实跑 CRISPRon；前端/调用方必须如实展示来源）
- efficiency_score：meta_model_hier_bb_nob879_0921.joblib 形态二公式

运行（cs_pipeline/ 下）：
    python scripts/26_bulk_score_genome.py
    python scripts/26_bulk_score_genome.py --max-rows 50000   # 冒烟
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from genet.predict import SpCas9

import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from scripts.features_common import FEATURE_COLS, seq_features  # noqa: E402
from scripts.crispron_scorer import (  # noqa: E402
    SOURCE_APPROXIMATED,
    CrispronScorer,
    no_real_runner,
)

IN_CSV = BASE / "results" / "grna_candidates_lettuce_0923.csv"
OUT_DIR = BASE / "results" / "scored_genome"
MODEL_PATH = BASE / "results" / "meta_model_hier_bb_nob879_0921.joblib"
MANIFEST = OUT_DIR / "scored_genome_manifest.json"
CHUNK = 20000


def load_meta():
    meta = joblib.load(MODEL_PATH)
    if isinstance(meta, dict) and "beta" in meta:
        feats = list(meta.get("feature_cols", FEATURE_COLS))
        assert feats == FEATURE_COLS, f"feature_cols mismatch: {feats}"
        return meta
    raise RuntimeError(f"期望形态二 GLMM 字典模型: {MODEL_PATH}")


def score_block(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    out = df.copy()
    feat = seq_features(out["seq30"].astype(str))
    for c in feat.columns:
        out[c] = feat[c].values

    tf.compat.v1.reset_default_graph()
    sp = SpCas9()
    pred = sp.predict(out["seq30"].astype(str).tolist())
    deep = np.asarray(pred["SpCas9"].values, dtype=float)
    out["deepspcas9_score"] = np.round(deep, 4)
    scored = CrispronScorer(real_runner=no_real_runner).score(
        out["seq30"].astype(str), out["deepspcas9_score"], out["tm"]
    )
    out["crispron_score"] = scored["crispron_score"]
    out["crispron_source"] = scored["crispron_source"]

    X = out[FEATURE_COLS].astype(float).values
    Z = (X - meta["mu"]) / meta["std"]
    logits = meta["beta0"] + np.dot(Z, meta["beta"])
    probs = 1.0 / (1.0 + np.exp(-logits))
    out["efficiency_score"] = np.clip(probs * 100.0, 0.0, 100.0).round(2)
    out["efficiency_placeholder"] = (
        100 - (out["gc_total"] * 100 - 50).abs() * 1.5 - (out["tm"] - 62).abs() * 0.8
    ).round(1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows", type=int, default=0, help=">0 时只打分前 N 行（冒烟）")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = load_meta()

    reader = pd.read_csv(IN_CSV, chunksize=args.chunk)
    n_done = 0
    t0 = time.time()
    part_id = 0

    for chunk in reader:
        if args.max_rows and n_done >= args.max_rows:
            break
        if args.max_rows and n_done + len(chunk) > args.max_rows:
            chunk = chunk.iloc[: args.max_rows - n_done]

        part_path = OUT_DIR / f"part_{part_id:06d}.csv"
        # 断点续跑：仅当分片已存在且行数与本块一致时跳过；不完整分片会被重写补齐。
        # 扫描大表等历史产物永不删除。先检查再打分，避免跳过块仍做无用推理。
        if part_path.exists():
            try:
                existing_rows = sum(1 for _ in part_path.open("r", encoding="utf-8")) - 1
            except OSError:
                existing_rows = -1
            if existing_rows == len(chunk):
                n_done += len(chunk)
                part_id += 1
                print(f"skip complete {part_path.name} (rows so far {n_done})", flush=True)
                continue
            print(
                f"rewrite incomplete {part_path.name} (had {existing_rows}, need {len(chunk)})",
                flush=True,
            )

        scored = score_block(chunk, meta)

        scored.to_csv(part_path, index=False)
        n_done += len(scored)
        elapsed = time.time() - t0
        rate = n_done / elapsed if elapsed > 0 else 0
        print(
            f"part_{part_id:06d} rows={len(scored)} total={n_done} "
            f"{rate:.0f}/s elapsed={elapsed:.0f}s",
            flush=True,
        )
        part_id += 1

        MANIFEST.write_text(
            json.dumps(
                {
                    "input": str(IN_CSV),
                    "rows_scored": n_done,
                    "parts": part_id,
                    "crispron_source": SOURCE_APPROXIMATED,
                    "model": MODEL_PATH.name,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"DONE rows={n_done} parts={part_id} out={OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
