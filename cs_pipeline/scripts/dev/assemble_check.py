# -*- coding: utf-8 -*-
import pandas as pd, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads

def assemble_ref(block_rows_with_header):
    """用 header 行 + 所有 WT 行拼最长 amplicon"""
    amp=''
    # 先 header
    for h in block_rows_with_header:
        s = str(h['header']['Left reads seq'])
        if s not in ('nan',''): amp = merge_reads(amp, s)
    wt = [v for b in block_rows_with_header for v in b['vars']
          if v['Left variation type']=='WT' and v['Right variation type']=='WT']
    for v in wt:
        amp = merge_reads(amp, str(v['Left reads seq']))
        amp = merge_reads(amp, str(v['Right reads seq']))
    return amp

# 已有 guide 表
m = pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet1')
known = set(zip(m['seq-20'], m['pam']))
known_seqs = set(m['seq-20'])
extra = pd.read_csv('data/hitom/hitom_seq30_full_0916.csv')
extra_seqs = set(extra['seq20'].astype(str))
print(f"主表唯一seq20={len(known_seqs)}, hitom_seq30 seq20数={len(extra_seqs)}")

comp = str.maketrans('ACGT','TGCA')
def rc(s): return s.translate(comp)[::-1]

import glob
for f in sorted(glob.glob('NEWdata/02_HiTOM结果表格/*/*.xls')):
    d=load_hitom(f); blocks=split_blocks(d)
    refs={}
    for b in blocks: refs.setdefault(b['ref'],[]).append(b)
    print(f"\n=== {os.path.basename(f)[:50]} ===")
    for ref, bl in refs.items():
        amp = assemble_ref(bl)
        hits=[]
        for s in known_seqs:
            i = amp.find(s)
            if i>=0: hits.append(('主表',s,'+',i,amp[i+20:i+23]))
            j = rc(amp).find(s)
            if j>=0: hits.append(('主表',s,'-',j,rc(amp)[j+20:j+23]))
        for s in extra_seqs:
            if not isinstance(s,str) or len(s)!=20: continue
            i = amp.find(s)
            if i>=0: hits.append(('hitom487',s,'+',i,amp[i+20:i+23]))
            j = rc(amp).find(s)
            if j>=0: hits.append(('hitom487',s,'-',j,rc(amp)[j+20:j+23]))
        print(f"  {ref}: amplicon={len(amp)}bp 命中={hits if hits else '无'}")
