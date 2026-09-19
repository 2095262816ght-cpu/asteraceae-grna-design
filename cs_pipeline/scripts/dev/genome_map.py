# -*- coding: utf-8 -*-
"""把所有 ref 的 amplicon 比对到 3 个参考基因组"""
import pandas as pd, re, sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads

def load_genome(path):
    seqs={}; name=None; buf=[]
    with open(path) as f:
        for ln in f:
            if ln.startswith('>'):
                if name: seqs[name]=''.join(buf).upper()
                name=ln[1:].split()[0]; buf=[]
            else: buf.append(ln.strip())
    if name: seqs[name]=''.join(buf).upper()
    return seqs

GENOMES = {
 'TKS':        ('data/reference_genomes/2-1_TKS.genome.fasta','data/reference_genomes/2-2_TKS.genome.gff3'),
 'StemLettuce':('data/reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa','data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff'),
 'LsT2T':      ('data/reference_genomes/3-1_LsT2T.genome.fa','data/reference_genomes/3-1_LsT2T.annotation.gff3'),
}
comp = str.maketrans('ACGT','TGCA')
def rc(s): return s.translate(comp)[::-1]

def assemble_ref(bl):
    amp=''
    for h in bl:
        amp = merge_reads(amp, str(h['header']['Left reads seq']))
        amp = merge_reads(amp, str(h['header']['Right reads seq']))
    wt=[v for b in bl for v in b['vars'] if v['Left variation type']=='WT' and v['Right variation type']=='WT']
    for v in wt:
        amp = merge_reads(amp, str(v['Left reads seq']))
        amp = merge_reads(amp, str(v['Right reads seq']))
    return amp

# 1. 收集所有 ref 的 amplicon（跨批次合并）
ref_blocks={}
for f in sorted(glob.glob('NEWdata/02_HiTOM结果表格/*/*.xls')):
    blocks=split_blocks(load_hitom(f))
    for b in blocks: ref_blocks.setdefault(b['ref'],[]).append(b)

amps={}
for ref, bl in ref_blocks.items():
    amps[ref]=assemble_ref(bl)
    print(f"{ref:14s} amplicon={len(amps[ref])}bp")

# 2. 比对
print("\n=== 基因组比对 ===")
genomes={k: load_genome(v[0]) for k,v in GENOMES.items()}
results={}
for ref, amp in amps.items():
    if len(amp)<50:
        print(f"{ref:14s} [amplicon太短]"); continue
    hits=[]
    for gname, gs in genomes.items():
        for chrom, seq in gs.items():
            i = seq.find(amp)
            if i>=0: hits.append((gname,chrom,i,i+len(amp),'+','exact'))
            j = seq.find(rc(amp))
            if j>=0: hits.append((gname,chrom,j,j+len(amp),'-','exact'))
    if not hits:
        # 降级：用 40bp kmer 探针
        probe = amp[len(amp)//2-20:len(amp)//2+20]
        for gname, gs in genomes.items():
            for chrom, seq in gs.items():
                i = seq.find(probe)
                if i>=0: hits.append((gname,chrom,i,i+40,'+','kmer40'))
                j = seq.find(rc(probe))
                if j>=0: hits.append((gname,chrom,j,j+40,'-','kmer40'))
    results[ref]=hits
    for h in hits[:4]:
        print(f"{ref:14s} -> {h[0]} {h[1]}:{h[2]}-{h[3]} {h[4]} ({h[5]})")
    if not hits: print(f"{ref:14s} -> 无命中")

with open('scripts/dev/amplicon_hits.json','w') as f:
    json.dump({r:[list(x) for x in hs] for r,hs in results.items()}, f, ensure_ascii=False, indent=1)
with open('scripts/dev/amplicons.json','w') as f:
    json.dump(amps, f)
