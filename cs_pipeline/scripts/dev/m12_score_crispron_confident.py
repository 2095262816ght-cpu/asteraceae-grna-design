# -*- coding: utf-8 -*-
"""12: 全量版 CRISPRon 打分（逻辑同 03，输入输出改全量文件，经 WSL 运行）。"""
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
IO = ROOT / "data" / "hitom" / "crispron_io"
IN_FA = IO / "seq30_in.fa"
OUT_DIR = IO / "out"

df = pd.read_csv(ROOT / "data" / "hitom" / "hitom_seq30_confident_0918.csv")
IO.mkdir(parents=True, exist_ok=True)
with open(IN_FA, "w") as f:
    for _, r in df.iterrows():
        f.write(f">{r.guide_id}\n{r.seq30}\n")

subprocess.run(
    ["wsl", "-d", "Ubuntu-22.04", "bash",
     "/mnt/" + str(ROOT).replace("\\", "/").replace(":", "").lower() + "/env/run_crispron_wsl.sh"],
    check=True)

res = pd.read_csv(OUT_DIR / "crispron.csv")
res["guide_id"] = res["ID"].str.replace(r"_[pm]_[0-9]+$", "", regex=True)
res = res.merge(df[["guide_id", "seq30"]], on="guide_id")
res = res[res["30mer"] == res["seq30"]]
out = res[["guide_id", "CRISPRon"]].rename(columns={"CRISPRon": "crispron_score"})
assert len(out) == len(df), f"行数不符: {len(out)} vs {len(df)}（有 guide 未打出分，需排查）"
out.to_csv(ROOT / "results" / "scores_crispron_confident_0918.csv", index=False)
print(f"OK: {len(out)} rows -> results/scores_crispron_confident_0918.csv")
