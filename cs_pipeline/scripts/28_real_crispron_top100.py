"""28: 进库 Top100 真实 CRISPRon 批量打分（WSL 并行批处理，断点续跑）。

背景：scripts/26 全量打分时 crispron_score 用经验近似式伪造（crispron_source=approximated），
方案 3 是只对进库的 Top100 候选补跑真实 CRISPRon。75 小时旧口径的元凶是小批量
（500/块）下每块 10.6s 固定开销 + 逐块跨系统调用；本脚本用大块（默认 20000/块）
摊薄固定开销、多 worker 并行吃满 CPU、按块落盘断点续跑。

输入：results/lettuce_all_genes_top100_candidates.csv（4,529,490 行）
      全局按 seq30 去重后实跑（重复序列只需算一次），实测唯一序列 3,998,591 条。
输出：results/real_crispron_top100_0927.csv（seq30, crispron_score，append+断点续跑）
      失败块记录在 results/real_crispron_top100_0927.failed.txt

取值约定与 crispron_wsl.score / scripts/03 逐条一致（30mer 精确匹配过滤）。
实测吞吐（本机 WSL Ubuntu-22.04 / 16 核）：固定 ~10.6s/块、边际 ~7.4ms/条，
单 worker 约 8.2h，8 workers 预计 1.5h 内。

运行（cs_pipeline/ 下）：
    python scripts/28_real_crispron_top100.py --max-seqs 20000   # 冒烟（1 块）
    python scripts/28_real_crispron_top100.py                    # 全量
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from scripts import crispron_wsl as cw  # noqa: E402

IN_CSV = BASE / "results" / "lettuce_all_genes_top100_candidates.csv"
OUT_CSV = BASE / "results" / "real_crispron_top100_0927.csv"
FAILED_TXT = BASE / "results" / "real_crispron_top100_0927.failed.txt"

_lock = threading.Lock()


def load_done() -> set[str]:
    if not OUT_CSV.exists():
        return set()
    done = pd.read_csv(OUT_CSV, usecols=["seq30"])
    return set(done["seq30"].astype(str))


def write_rows(rows: list[tuple[str, float]]) -> None:
    with _lock:
        header = not OUT_CSV.exists()
        with open(OUT_CSV, "a", encoding="ascii", newline="") as fh:
            if header:
                fh.write("seq30,crispron_score\n")
            for s, v in rows:
                fh.write(f"{s},{v}\n")


def score_chunk(chunk_id: int, seqs: list[str], timeout_s: int) -> tuple[int, int, int]:
    """单块打分并落盘；失败降半重试一次。返回 (成功数, 失败数, 耗时s)。"""
    t0 = time.time()
    for attempt, sz in ((0, len(seqs)), (1, max(200, len(seqs) // 4))):
        if attempt == 1 and len(seqs) == sz:
            break
        out = {}
        for i in range(0, len(seqs), sz):
            out.update(cw._score_chunk(seqs[i : i + sz], timeout_s))
        if len(out) >= 0.98 * len(seqs):
            write_rows(list(out.items()))
            missing = [s for s in seqs if s not in out]
            if missing:
                with _lock:
                    with open(FAILED_TXT, "a", encoding="ascii") as fh:
                        fh.writelines(f"{s}\n" for s in missing)
            return len(out), len(missing), int(time.time() - t0)
    with _lock:
        with open(FAILED_TXT, "a", encoding="ascii") as fh:
            fh.writelines(f"{s}\n" for s in seqs)
    return 0, len(seqs), int(time.time() - t0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=20000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--max-seqs", type=int, default=0, help="冒烟用：只跑前 N 条唯一序列")
    args = ap.parse_args()

    if not cw.is_available(timeout_s=60):
        raise SystemExit("WSL CRISPRon 管线不可用，终止。")

    df = pd.read_csv(IN_CSV, usecols=["seq30"])
    uniq = list(dict.fromkeys(df["seq30"].astype(str)))
    done = load_done()
    todo = [s for s in uniq if s not in done]
    if args.max_seqs:
        todo = todo[: args.max_seqs]
    print(f"唯一序列 {len(uniq)}，已完成 {len(done)}，本次待跑 {len(todo)}")

    chunks = [todo[i : i + args.chunk] for i in range(0, len(todo), args.chunk)]
    if not chunks:
        print("无待跑序列，退出。")
        return

    t0 = time.time()
    n_ok = n_fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(score_chunk, i, c, args.timeout): i for i, c in enumerate(chunks)}
        for fut in as_completed(futs):
            ok, fail, dt = fut.result()
            n_ok += ok
            n_fail += fail
            el = time.time() - t0
            rate = n_ok / el if el > 0 else 0
            eta = (len(todo) - n_ok - n_fail) / rate / 60 if rate > 0 else -1
            print(f"[{n_ok + n_fail}/{len(todo)}] ok={ok} fail={fail} chunk={dt}s "
                  f"rate={rate:.0f}/s eta={eta:.0f}min", flush=True)

    print(f"完成：成功 {n_ok}，失败 {n_fail}，总耗时 {(time.time()-t0)/60:.1f} min")
    print(f"结果：{OUT_CSV}")
    if n_fail:
        print(f"失败序列清单：{FAILED_TXT}")


if __name__ == "__main__":
    main()
