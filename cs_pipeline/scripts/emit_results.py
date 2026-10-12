# -*- coding: utf-8 -*-
"""一键生成《附件5 代码提交要求》第四节规定的标准化最终结果文件 results.csv。

主运行入口：本脚本负责「读取规定输入 → 生成最终结果文件」；
新序列的模型打分入口为 `scripts/predict.py` 的 `predict_efficiency()` / `predict_details()`。

用法
----
    python scripts/emit_results.py                       # 默认：从已打分候选库生成 results/results.csv
    python scripts/emit_results.py --source <csv>        # 指定已打分候选库
    python scripts/emit_results.py --output <csv>        # 指定输出路径

仅依赖 pandas，不需要 tensorflow / genet / CRISPRon 环境。
字段规范见 results/RESULTS_SCHEMA.md。
"""

import argparse
import csv
import heapq
import os
import shutil
import sys
import tempfile

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(BASE, "results", "lettuce_all_genes_top100_candidates.csv")
DEFAULT_OUTPUT = os.path.join(BASE, "results", "results.csv")

TRACK = "赛道二：AI基因编辑与核酸工具设计"
MODEL = "meta_model_hier_bb_nob879_0921.joblib（分层选择性 Beta-Binomial GLMM）"
VERSION = "v2.1（2026-09-25 指标冻结）"

HEADER = [
    "候选编号", "所属赛道", "靶基因ID", "染色体", "起点", "终点", "链",
    "候选序列(20nt)", "PAM", "候选序列上下文(30nt)", "区域类型",
    "预测编辑效率", "DeepSpCas9打分", "CRISPRon打分", "GC含量", "Tm(℃)",
    "polyT标志", "对应模型", "运行版本", "备注",
]

USECOLS = ["guide_id", "gene_id", "chrom", "start", "end", "strand",
           "seq20", "pam", "region_type", "seq30", "gc_total", "tm",
           "deepspcas9_score", "crispron_score", "crispron_source",
           "efficiency_score", "poly_t"]

# 结果行下标：用于排序键
IDX_EFF, IDX_DEEP, IDX_ID = 11, 12, 0
CHUNKSIZE = 250_000


def num(v, nd):
    """缺失值规则：缺失输出空字符串，不编造、不插补、不以 0 代替。"""
    if v is None:
        return ""
    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "na", "null"):
        return ""
    try:
        return f"{float(s):.{nd}f}"
    except ValueError:
        return ""


def build_row(r):
    try:
        poly_n = int(float(r["poly_t"]))
    except (TypeError, ValueError):
        poly_n = 0

    notes = []
    if poly_n > 0:
        notes.append(f"polyT={poly_n}，终止子风险")
    if str(r.get("crispron_source", "")).strip() not in ("", "wsl_real"):
        notes.append(f"CRISPRon来源={r['crispron_source']}")
    if "N" in str(r["seq20"]).upper():
        notes.append("序列含N")

    return [
        str(r["guide_id"]), TRACK, str(r["gene_id"]), str(r["chrom"]),
        num(r["start"], 0), num(r["end"], 0), str(r["strand"]),
        str(r["seq20"]), str(r["pam"]), str(r["seq30"]), str(r["region_type"]),
        num(r["efficiency_score"], 2), num(r["deepspcas9_score"], 4),
        num(r["crispron_score"], 2), num(r["gc_total"], 4), num(r["tm"], 2),
        str(poly_n), MODEL, VERSION, "；".join(notes),
    ]


def sort_key(row):
    """排序逻辑：预测编辑效率降序 → DeepSpCas9 打分降序 → 候选编号升序（确定性）。"""
    def f(i):
        try:
            return -float(row[i])
        except ValueError:
            return 0.0
    return (f(IDX_EFF), f(IDX_DEEP), row[IDX_ID])


def emit(source, output):
    workdir = tempfile.mkdtemp(prefix="emit_results_")
    try:
        parts = []
        total = 0
        for ci, chunk in enumerate(pd.read_csv(source, usecols=USECOLS,
                                               chunksize=CHUNKSIZE)):
            rows = [build_row(r) for r in chunk.to_dict("records")]
            rows.sort(key=sort_key)
            p = os.path.join(workdir, f"part_{ci:04d}.csv")
            with open(p, "w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerows(rows)
            parts.append(p)
            total += len(rows)
            print(f"  分块 {ci + 1}: {len(rows)} 行", flush=True)

        print(f"合计 {total} 行 / {len(parts)} 分块，归并排序中...", flush=True)
        streams = [open(p, "r", newline="", encoding="utf-8") for p in parts]
        try:
            with open(output, "w", newline="", encoding="utf-8") as out:
                w = csv.writer(out)
                w.writerow(HEADER)
                w.writerows(heapq.merge(*(csv.reader(s) for s in streams),
                                        key=sort_key))
        finally:
            for s in streams:
                s.close()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"完成 → {output}  ({os.path.getsize(output) / 2 ** 20:.1f} MiB)")
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成附件5 标准化最终结果文件 results.csv")
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help="已打分候选库 CSV（默认 results/lettuce_all_genes_top100_candidates.csv）")
    ap.add_argument("--output", default=DEFAULT_OUTPUT,
                    help="输出路径（默认 results/results.csv）")
    a = ap.parse_args(argv)

    if not os.path.exists(a.source):
        print(f"输入不存在: {a.source}", file=sys.stderr)
        return 2
    missing = [c for c in ("efficiency_score",) if c not in
               pd.read_csv(a.source, nrows=0).columns]
    if missing:
        print(f"输入缺少必需列: {missing}", file=sys.stderr)
        return 2

    print(f"源: {a.source}")
    emit(a.source, a.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
