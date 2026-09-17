import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def revcomp(s): return s.translate(str.maketrans("ACGT","TGCA"))[::-1]

genome={}; cur=None
for line in open(r"cs_pipeline\data\reference_genomes\2-1_TKS.genome.fasta"):
    if line.startswith(">"): cur=line[1:].split()[0]; genome[cur]=[]
    elif cur: genome[cur].append(line.strip().upper())
genome={k:"".join(v) for k,v in genome.items()}
lg07 = genome["LG07"]

refs = {}
for path in [r"cs_pipeline\data\raw\hitom\R0_sequencing\20211224_transgenic_seedlings\Reference - 21.12.31.txt",
             r"cs_pipeline\data\raw\hitom\R1_sequencing\unsorted\re-2022.6.14.txt"]:
    name=None
    for line in open(path, encoding="utf-8", errors="replace"):
        line=line.strip()
        if line.startswith(">"): name=line[1:].strip()
        elif line and name: refs.setdefault(name, line.upper())

for name, s in refs.items():
    i = lg07.find(s)
    ori = "+"
    if i < 0:
        i = lg07.find(revcomp(s)); ori="-(展示为负链)"
    if i >= 0:
        print(f"{name}: 长{len(s)}bp, 对应正链 {i+1}..{i+len(s)}, 方向={ori}")
    else:
        print(f"{name}: LG07 未命中")

print()
# 三个候选位点
sites = [("表内记录guide(5712)", "GAAAATATTGAAAACATATA"),
         ("推断真实guide(热点)", "GAAAATGTCAGGATGCCTGA"),
         ("训练集里的CATT guide", "CATTACCAAAATAAAACAGG")]
for name, g in sites:
    ip = lg07.find(g); im = lg07.find(revcomp(g))
    print(f"{name} {g}: 正链直接命中={ip+1 if ip>=0 else '无'}, revcomp命中={im+1 if im>=0 else '无'}")

# SP3 参考(负链展示)内, 各位点的展示位置
sp3 = refs.get("SP3","")
if sp3:
    print("\nSP3 参考序列内(展示方向, 0-based):")
    for probe, label in [("TATATGTTTTCAATATTTTC","记录guide的revcomp"),
                         ("GAAAATGTCAGGATGCCTGA","推断真实guide(负链)"),
                         ("CATTACCAAAATAAAACAGG","CATT guide原样"),
                         (revcomp("CATTACCAAAATAAAACAGG"),"CATT guide的revcomp")]:
        j = sp3.find(probe)
        print(f"  {label}: {'位置 '+str(j) if j>=0 else '不含'}")
