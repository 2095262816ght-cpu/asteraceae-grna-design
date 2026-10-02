"""DeepSpCas9 + Stacking 集成打分 CLI（由 app/inference_client.py 以子进程方式调用）。

设计原因：genet 锁定 tensorflow<2.10 → protobuf<3.20，与宿主服务环境的依赖约束冲突，
因此打分跑在独立的 crispr 环境中，宿主进程通过 stdin/stdout 与之通信。

用法：
    echo "ATCGGCTAAGCTAGGCTAGCATCGTGGATC" | python score_deepspcas9_cli.py

输入：stdin，每行一条 30bp 序列（4nt 上游 + 20nt guide + NGG PAM + 3nt 下游）。
输出：stdout，CSV，列 seq30,deepspcas9_score,crispron_score,crispron_source,stacking_score；顺序与输入一一对应。
      crispron_source = wsl_real（经 WSL 实跑真实 CRISPRon）或 approximated（近似式降级），
      调用方须据此向用户标注，不得把降级值当真实模型输出展示。
异常：任何错误写入 stderr 并以非零码退出，由调用方展示。
"""
import csv
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from scripts.predict import predict_details


def main() -> int:
    seqs = [line.strip().upper() for line in sys.stdin if line.strip()]
    if not seqs:
        print("no sequences on stdin", file=sys.stderr)
        return 2

    res_df = predict_details(seqs)
    writer = csv.writer(sys.stdout)
    writer.writerow(["seq30", "deepspcas9_score", "crispron_score", "crispron_source", "stacking_score"])
    for _, row in res_df.iterrows():
        writer.writerow([
            row["seq30"],
            f"{float(row['deepspcas9_score']):.4f}",
            f"{float(row['crispron_score']):.4f}",
            str(row["crispron_source"]),
            f"{float(row['stacking_score']):.2f}",
        ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
