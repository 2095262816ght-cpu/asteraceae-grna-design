# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads

d=load_hitom('NEWdata/02_HiTOM结果表格/USR-14333-SY7249/all-SY7249-USR-14333-Hi-TOM-sequencing-result.xls')
blocks=split_blocks(d)
sm1=[b for b in blocks if b['ref']=='refsm1']
wt=[v for b in sm1 for v in b['vars'] if v['Left variation type']=='WT' and v['Right variation type']=='WT']
print("WT行数:", len(wt))
amp=''
for v in wt[:3]:
    l=str(v['Left reads seq']); r=str(v['Right reads seq'])
    print(f"L({len(l)}): {l[:40]}...")
    amp = merge_reads(amp, l); print("  merge L ->", len(amp))
    amp = merge_reads(amp, r); print("  merge R ->", len(amp))
