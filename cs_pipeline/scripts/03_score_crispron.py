"""03: CRISPRon 打分（官方 TF2 仓库，经 WSL 运行），产出 results/scores_crispron_0911.csv。

降级方案1：crisprScore 无 CRISPRon 函数，改用 RTH-tools/CRISPRon（tools/CRISPRon，
由 env/setup_crispron_wsl.sh 在 WSL Ubuntu-22.04 中组装）。
流程：seq30 -> fasta -> WSL 跑 CRISPRon.sh -> 解析 crispron.csv 回并主表。
"""
import shutil
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IO = ROOT / "data" / "hitom" / "crispron_io"
IN_FA = IO / "seq30_in.fa"
OUT_DIR = IO / "out"

df = pd.read_csv(ROOT / "data" / "hitom" / "hitom_seq30_0909.csv")
IO.mkdir(parents=True, exist_ok=True)
with open(IN_FA, "w") as f:
    for _, r in df.iterrows():
        f.write(f">{r.guide_id}\n{r.seq30}\n")

def wsl_available() -> bool:
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "true"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def git_bash() -> str:
    """定位可用的 Git Bash（MSYS/MINGW）。

    不能直接用裸 "bash"：Windows CreateProcess 先搜 System32，
    会命中 WSL 占位的 bash.exe（WSL 缺失时直接 exit 1）。
    """
    cands = [shutil.which("bash"),
             r"C:\Program Files\Git\bin\bash.exe",
             r"C:\Program Files\Git\usr\bin\bash.exe",
             r"C:\Program Files (x86)\Git\bin\bash.exe"]
    for c in cands:
        if not c or not Path(c).exists() or "system32" in c.lower():
            continue
        try:
            r = subprocess.run([c, "-c", "uname -s"],
                               capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and any(k in r.stdout for k in ("MINGW", "MSYS", "CYGWIN")):
                return c
        except Exception:
            continue
    raise RuntimeError("未找到可用的 Git Bash（System32 下的 bash 是 WSL 占位，不可用）")


if wsl_available():
    subprocess.run(
        ["wsl", "-d", "Ubuntu-22.04", "bash",
         "/mnt/d/lifesciencechallenge/cs_pipeline/env/run_crispron_wsl.sh"],
        check=True)
else:
    # WSL 不可用（如发行版被移除）时降级到 Windows 原生路线：
    # crispron-win 环境 + tools/win-shims，9.9 已验证与官方输出逐字节一致，
    # 见 env/crispron_win_native_0909.md。
    print("WSL Ubuntu-22.04 不可用，降级到 Windows 原生 CRISPRon（crispron-win 环境）")
    subprocess.run([git_bash(), str(ROOT / "env" / "run_crispron_win.sh")], check=True)

res = pd.read_csv(OUT_DIR / "crispron.csv")
res["guide_id"] = res["ID"].str.replace(r"_[pm]_[0-9]+$", "", regex=True)
# 输入恰为 30nt 时正/反链各至多产生一个 30mer 窗口；只保留与输入 seq30 完全一致的行
res = res.merge(df[["guide_id", "seq30"]], on="guide_id")
res = res[res["30mer"] == res["seq30"]]
out = res[["guide_id", "CRISPRon"]].rename(columns={"CRISPRon": "crispron_score"})
assert len(out) == len(df), f"行数不符: {len(out)} vs {len(df)}（有 guide 未打出分，需排查）"
out.to_csv(ROOT / "results" / "scores_crispron_0911.csv", index=False)
print(f"OK: {len(out)} rows -> results/scores_crispron_0911.csv")
