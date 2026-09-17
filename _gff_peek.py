import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 看 GFF3 里 LG03.2345 相关的行
p = r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-2_TKS.genome.gff3"
with open(p, encoding="utf-8", errors="ignore") as f:
    n = 0
    for line in f:
        if "2345" in line and "LG03" in line:
            print(line.rstrip()[:200])
            n += 1
            if n > 15:
                break
print("---")
with open(p, encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        if i < 15 or ("gene" in line.split("\t")[2] if len(line.split("\t")) > 2 else False):
            print(line.rstrip()[:200])
        if i > 40:
            break
