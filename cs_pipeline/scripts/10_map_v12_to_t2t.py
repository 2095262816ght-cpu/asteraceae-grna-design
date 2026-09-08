# v1.2 (Ls01G*) -> T2T (LsaT2T*) CDS 序列映射
# 策略: 1) 全长精确匹配; 2) k-mer (k=25) 共享计数找最佳候选后计算一致性
# 输出: v12_to_t2t_mapping.csv (v12_id, t2t_gene, identity_pct, match_method)
import csv
import gzip
import re
from collections import defaultdict

V12_CDS = "data/lettuce/v12_CDS.fasta.gz"   # v1.2 CDS（NGDC GWHERDY00000000，本地自备）
T2T_CDS = "data/lettuce/t2t_CDS.fasta"      # 由 09_extract_t2t_cds.py 生成
OUT = "results/v12_to_t2t_mapping.csv"
K = 25


def load_t2t(path):
    seqs, name, buf = {}, None, []
    with open(path) as f:
        for line in f:
            if line.startswith(">"):
                if name:
                    seqs[name] = "".join(buf)
                name = line[1:].split()[0]
                buf = []
            else:
                buf.append(line.strip())
        if name:
            seqs[name] = "".join(buf)
    return seqs


def load_v12(path):
    seqs, name, buf = {}, None, []
    with gzip.open(path, "rt", errors="replace") as f:
        for line in f:
            if line.startswith(">"):
                if name:
                    seqs[name] = "".join(buf)
                m = re.search(r"OriID=(\S+)", line)
                name = m.group(1) if m else None
                buf = []
            else:
                buf.append(line.strip())
        if name:
            seqs[name] = "".join(buf)
    return seqs


def kmers(s, k=K, stride=3):
    return {s[i:i + k] for i in range(0, max(1, len(s) - k + 1), stride)}


def identity(a, b):
    """简单重叠一致性: 以短序列每 k=15 seed 定位后算最长公共子串占比的近似。
    这里用逐位比对(等长)或最优偏移估计(不等长)。"""
    if not a or not b:
        return 0.0
    if len(a) == len(b):
        return 100.0 * sum(1 for x, y in zip(a, b) if x == y) / len(a)
    # 不等长: 用 k-mer 锚点估计一致性
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    k = 15
    idx = defaultdict(list)
    for i in range(0, len(long_) - k + 1):
        idx[long_[i:i + k]].append(i)
    best_shift, best_hits = 0, 0
    shifts = defaultdict(int)
    for i in range(0, len(short) - k + 1, 5):
        km = short[i:i + k]
        for j in idx.get(km, ()):  # 记录偏移
            shifts[j - i] += 1
    if shifts:
        best_shift, best_hits = max(shifts.items(), key=lambda kv: kv[1])
    # 在最优偏移下逐位比对
    matches = 0
    for i, c in enumerate(short):
        j = i + best_shift
        if 0 <= j < len(long_) and long_[j] == c:
            matches += 1
    return 100.0 * matches / max(len(short), len(long_))


def main():
    print("loading v1.2 CDS...", flush=True)
    v12 = load_v12(V12_CDS)
    print(f"  {len(v12)} sequences", flush=True)
    print("loading T2T CDS...", flush=True)
    t2t = load_t2t(T2T_CDS)
    print(f"  {len(t2t)} sequences", flush=True)

    # 精确匹配索引
    print("building exact-match index...", flush=True)
    t2t_by_seq = defaultdict(list)
    for gid, s in t2t.items():
        t2t_by_seq[s].append(gid)

    # k-mer 倒排索引 (stride 采样减小内存)
    print("building k-mer index...", flush=True)
    kidx = defaultdict(list)
    for gid, s in t2t.items():
        for km in kmers(s):
            kidx[km].append(gid)

    rows, n_exact, n_kmer, n_fail = [], 0, 0, 0
    t2t_gene_of = lambda mrna: mrna.split(".")[0]
    for i, (v12_id, seq) in enumerate(sorted(v12.items())):
        if i % 5000 == 0:
            print(f"  {i}/{len(v12)} (exact {n_exact}, kmer {n_kmer}, fail {n_fail})", flush=True)
        hits = t2t_by_seq.get(seq)
        if hits:
            rows.append((v12_id, t2t_gene_of(hits[0]), 100.0, "exact"))
            n_exact += 1
            continue
        cnt = defaultdict(int)
        for km in kmers(seq):
            for g in kidx.get(km, ()):
                cnt[g] += 1
        if not cnt:
            rows.append((v12_id, "", 0.0, "unmapped"))
            n_fail += 1
            continue
        cand, _ = max(cnt.items(), key=lambda kv: kv[1])
        ident = identity(seq, t2t[cand])
        if ident >= 80.0:
            rows.append((v12_id, t2t_gene_of(cand), round(ident, 2), "kmer"))
            n_kmer += 1
        else:
            rows.append((v12_id, "", round(ident, 2), "unmapped"))
            n_fail += 1

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["v12_id", "t2t_gene", "identity_pct", "match_method"])
        w.writerows(rows)
    print(f"DONE: exact {n_exact}, kmer {n_kmer}, unmapped {n_fail} / total {len(rows)}", flush=True)
    print("->", OUT, flush=True)


if __name__ == "__main__":
    main()
