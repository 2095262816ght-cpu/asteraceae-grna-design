"""B4: 合并 demo 所需数据 -> demo/app_data.csv

数据源（相对 cs_pipeline 根目录）：
- data/demo/demo_nlr50_candidates.csv     B2 候选（49 个 NLR 基因，19,839 条）
- results/offtarget_counts_0924.csv  B3 脱靶计数（缺失则以 NaN 占位，跑完后重跑本脚本接入）
- data/lettuce/centromere_regions.bed 着丝粒区间
- data/demo/demo_nlr50_genes.txt + nlr 注释（d:/生物/LSC_共享/data/lettuce_t2t/nlr_with_coords.csv）
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent          # cs_pipeline/
SHARED = Path(r"d:\生物\LSC_共享\data\lettuce_t2t")      # 主数据目录（大文件不入库）

cand = pd.read_csv(BASE / "data/demo/demo_nlr50_candidates.csv")

# --- 脱靶计数（B3 产出，可能尚未生成） ---
off_path = BASE / "results/offtarget_counts_0924.csv"
if off_path.exists():
    off = pd.read_csv(off_path)
    cand = cand.merge(off, on="guide_id", how="left")
    offstatus = f"merged {off_path.name} ({off_path.stat().st_size/1e6:.1f} MB)"
else:
    for c in ("exact_match_count", "offtarget_count_mis1", "offtarget_count_mis2", "offtarget_count_mis3"):
        cand[c] = pd.NA
    offstatus = "offtarget_counts_0924.csv NOT READY - placeholder NaN"

# --- 着丝粒过滤标记 ---
# 注意：bed 的染色体名为 Chr1..Chr9，候选表为 Chr01..Chr09（T2T 命名），
# 统一规范化为无零填充数字键再匹配（9.27 修复：此前直接按字符串匹配，恒为 False）。
def _norm_chrom(c):
    c = str(c).strip()
    if c.lower().startswith("chr"):
        c = c[3:]
    return str(int(c)) if c.isdigit() else c

cen = pd.read_csv(BASE / "data/lettuce/centromere_regions.bed", sep="\t",
                  header=None, names=["chrom", "cstart", "cend"])
cen_map = {_norm_chrom(r.chrom): (r.cstart, r.cend) for r in cen.itertuples()}


def in_centromere(row):
    rng = cen_map.get(_norm_chrom(row.chrom))
    if rng is None:
        return False
    return row.start < rng[1] and row.end > rng[0]

cand["in_centromere"] = cand.apply(in_centromere, axis=1)

# --- 序列特征 ---
cand["gc_pct"] = (cand.seq20.str.count(r"[GC]") / 20 * 100).round(1)

def tm_wallace(seq):
    return 2 * sum(1 for b in seq if b in "AT") + 4 * sum(1 for b in seq if b in "GC")

cand["tm_c"] = cand.seq20.map(tm_wallace)

# --- 效率分计算（Stacking 集成模型预测分，带启发式占位兜底） ---
cand["efficiency_placeholder"] = (
    100 - (cand.gc_pct - 50).abs() * 1.5 - (cand.tm_c - 62).abs() * 0.8
).round(1)

try:
    import sys
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from scripts.predict import predict_efficiency
    print("Scoring candidates with Stacking meta model...")
    batch_size = 5000
    all_scores = []
    seqs = cand.seq30.tolist()
    for i in range(0, len(seqs), batch_size):
        all_scores.extend(predict_efficiency(seqs[i : i + batch_size]))
    cand["efficiency_score"] = all_scores
    print(f"Stacking scoring complete: {len(all_scores)} guides scored.")
except Exception as e:
    print(f"Stacking scoring skipped ({e}), fallback to placeholder.")
    cand["efficiency_score"] = cand["efficiency_placeholder"]

# --- NLR 基因注释（供基因信息面板） ---
nlr_file = SHARED / "nlr_with_coords.csv"
if nlr_file.exists():
    nlr = pd.read_csv(nlr_file)
    nlr_cols = [c for c in ("t2t_gene_id", "chr", "start_bp", "end_bp", "strand", "nlr_type")
                if c in nlr.columns]
    genes = nlr[nlr_cols].rename(columns={"t2t_gene_id": "gene_id", "chr": "g_chrom",
                                          "start_bp": "g_start", "end_bp": "g_end",
                                          "strand": "g_strand"})
    demo_genes = pd.read_csv(BASE / "data/demo/demo_nlr50_genes.txt", header=None, names=["gene_id"])
    genes = genes.merge(demo_genes, on="gene_id")
    genes.to_csv(BASE / "demo/app_genes.csv", index=False)
elif (BASE / "demo/app_genes.csv").exists():
    genes = pd.read_csv(BASE / "demo/app_genes.csv")
else:
    genes = pd.DataFrame(columns=["gene_id", "g_chrom", "g_start", "g_end", "g_strand", "nlr_type"])

cand.to_csv(BASE / "demo/app_data.csv", index=False)
print(f"app_data.csv: {len(cand)} rows | genes: {len(genes)} | offtarget: {offstatus}")
print(f"centromere-flagged: {int(cand.in_centromere.sum())}")
