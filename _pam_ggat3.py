import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s):
    return s.translate(str.maketrans("ACGT", "TGCA"))[::-1]

genome = {}
cur = None
with open(r"D:\lifesciencechallenge\cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta") as f:
    for line in f:
        if line.startswith(">"):
            cur = line[1:].split()[0]
            genome[cur] = []
        elif cur:
            genome[cur].append(line.strip().upper())
genome = {k: "".join(v) for k, v in genome.items()}

seq = genome["LG01"]
# 以 guide=GGATTGCTGCTGAGAAGGCC, strand=-, PAM 在 guide 上游
probe = revcomp("GGATTGCTGCTGAGAAGGCC")  # 正链上找 revcomp
for pos in [seq.find(probe)]:
    idx = pos
    print(f"LG01 正链 revcomp命中 idx={idx+1}")
    print("正链片段 [idx-5, idx+23]:", seq[idx-5:idx+23])
    # guide 占据正链 [idx, idx+20), PAM 在负链意义上是 guide 上游 = 正链 [idx-3, idx)
    pam_pos_strand = seq[idx-3:idx]
    print(f"正链上游3bp = {pam_pos_strand}  ->  revcomp = {revcomp(pam_pos_strand)}")
    # 换个偏移试试：PAM 在 [idx-4, idx-1)?
    print("正链 [idx-4:idx-1]:", seq[idx-4:idx-1], "revcomp:", revcomp(seq[idx-4:idx-1]))
    print("正链 [idx-2:idx+1]:", seq[idx-2:idx+1], "revcomp:", revcomp(seq[idx-2:idx+1]))
