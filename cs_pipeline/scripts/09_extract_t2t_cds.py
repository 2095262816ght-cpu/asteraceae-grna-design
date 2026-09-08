# 从 T2T 基因组 fasta + GFF 提取所有 mRNA 的拼接 CDS 序列（无第三方依赖）
# 输出: t2t_CDS.fasta，header 为 >LsaT2TxxGxxxxx.1（mRNA ID）
import gzip
import re
import sys
from collections import defaultdict

GENOME = "data/lettuce/lettuce_t2t.fa"      # 大文件本地自备，不入库（见 cs_pipeline/.gitignore）
GFF = "data/lettuce/lettuce_t2t.gff3"
OUT = "data/lettuce/t2t_CDS.fasta"

COMP = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def revcomp(s):
    return s.translate(COMP)[::-1]


def parse_gff(path):
    mrna_cds = defaultdict(list)   # mrna_id -> [(chrom,start,end,strand,phase)]
    mrna_info = {}                 # mrna_id -> (gene_id, chrom, strand)
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) != 9:
                continue
            if p[2] == "mRNA":
                m_id = re.search(r"ID=([^;]+)", p[8]).group(1)
                m_par = re.search(r"Parent=([^;]+)", p[8]).group(1)
                mrna_info[m_id] = (m_par, p[0], p[6])
            elif p[2] == "CDS":
                par = re.search(r"Parent=([^;]+)", p[8]).group(1)
                mrna_cds[par].append((p[0], int(p[3]), int(p[4]), p[6]))
    return mrna_info, mrna_cds


def load_genome(path):
    seqs, name, buf = {}, None, []
    with open(path, "rt", encoding="ascii") as f:
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


def main():
    print("parsing gff...", flush=True)
    mrna_info, mrna_cds = parse_gff(GFF)
    print(f"  mRNA: {len(mrna_info)}, with CDS: {len(mrna_cds)}", flush=True)
    print("loading genome...", flush=True)
    genome = load_genome(GENOME)
    print(f"  chromosomes: {len(genome)}", flush=True)

    n_out = 0
    with open(OUT, "w", encoding="ascii") as out:
        for mrna, exons in mrna_cds.items():
            chrom = exons[0][0]
            strand = exons[0][3]
            seq_chrom = genome.get(chrom)
            if seq_chrom is None:
                continue
            exons.sort(key=lambda e: e[1])
            cds = "".join(seq_chrom[s - 1:e] for _, s, e, _ in exons)
            if strand == "-":
                cds = revcomp(cds)
            out.write(f">{mrna}\n")
            for i in range(0, len(cds), 70):
                out.write(cds[i:i + 70] + "\n")
            n_out += 1
    print(f"wrote {n_out} CDS sequences -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
