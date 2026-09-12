"""DeepSpCas9 打分 CLI（由 app/app.py 以子进程方式调用）。

设计原因：genet 锁定 tensorflow<2.10 → protobuf<3.20，与 streamlit 冲突，
因此打分跑在独立的 crispr 环境中，demo 进程通过 stdin/stdout 与之通信。

用法：
    echo "ATCGGCTAAGCTAGGCTAGCATCGTGGATC" | python score_deepspcas9_cli.py

输入：stdin，每行一条 30bp 序列（4nt 上游 + 20nt guide + NGG PAM + 3nt 下游）。
输出：stdout，CSV，列 seq30,deepspcas9_score；顺序与输入一一对应。
异常：任何错误写入 stderr 并以非零码退出，由调用方展示。
"""
import csv
import sys

import genet  # noqa: F401  提前导入以尽早暴露环境问题
from genet.predict import SpCas9


def main() -> int:
    seqs = [line.strip().upper() for line in sys.stdin if line.strip()]
    if not seqs:
        print("no sequences on stdin", file=sys.stderr)
        return 2

    df = SpCas9().predict(seqs)
    # genet 输出顺序与输入一致（Target 列回显输入序列）
    writer = csv.writer(sys.stdout)
    writer.writerow(["seq30", "deepspcas9_score"])
    for seq, score in zip(df["Target"], df["SpCas9"]):
        writer.writerow([seq, f"{float(score):.4f}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
