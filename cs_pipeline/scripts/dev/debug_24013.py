# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract2 import assemble_ref, rc

f='NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls'
blocks=split_blocks(load_hitom(f))
bl=[b for b in blocks if b['ref']=='ref24013gene3']
print("24013 块数:", len(bl))
amp=assemble_ref(bl)
print("amp len:", len(amp))
# 前两个块
for b0 in bl[:2]:
    print(f"\n=== block {b0['block']} ===")
    for v in b0['vars'][:6]:
        print(f"rn={v['Reads number']} ratio={v['Ratio']} {v['Left variation type']}/{v['Right variation type']} Lvar={v['Left variation']} Rvar={v['Right variation']}")
        print("   L:", str(v['Left reads seq'])[:130])
# 基因组定位
gen={}
name=None;buf=[]
with open('data/reference_genomes/2-1_TKS.genome.fasta') as fh:
    for ln in fh:
        if ln.startswith('>'):
            if name: gen[name]=''.join(buf).upper()
            name=ln[1:].split()[0];buf=[]
        else: buf.append(ln.strip())
    if name: gen[name]=''.join(buf).upper()
for g in ['AAGTCTCGATCTAATTTACA','GAGAGGGTGGACGTCCAAAC']:
    for chrom,seq in gen.items():
        i=seq.find(g); j=seq.find(rc(g))
        if i>=0 or j>=0:
            print(f"guide {g}: {chrom} {'+' if i>=0 else '-'} pos={i if i>=0 else j}")
i = None
for chrom,seq in gen.items():
    k=seq.find(amp)
    if k>=0: print("amplicon 正向命中", chrom, k, k+len(amp))
    k2=seq.find(rc(amp))
    if k2>=0: print("amplicon 反向命中", chrom, k2, k2+len(amp))
