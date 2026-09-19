# -*- coding: utf-8 -*-
import pandas as pd, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads, edit_profile

def debug_ref(f, refname, true_guides):
    d = load_hitom(f); blocks = split_blocks(d)
    rows = [v for b in blocks if b['ref']==refname for v in b['vars']]
    wt = [v for v in rows if v['Left variation type']=='WT' and v['Right variation type']=='WT']
    print(f"--- {refname}: 变异行={len(rows)} WT行={len(wt)}")
    amp=''
    for v in (wt if wt else rows):
        amp = merge_reads(amp, str(v['Left reads seq']))
        amp = merge_reads(amp, str(v['Right reads seq']))
        if len(amp)>150: break
    print(f"amplicon({len(amp)}): {amp}")
    comp = str.maketrans('ACGT','TGCA')
    rc = amp.translate(comp)[::-1]
    for g in true_guides:
        i = amp.find(g)
        j = rc.find(g)
        print(f"  真guide {g}: 正向位置={i} 反向位置={j}" + (f" (cut={i+17}, PAM={amp[i+20:i+23]})" if i>=0 else "") + (f" (rc中cut={j+17}, PAM={rc[j+20:j+23]})" if j>=0 else ""))
    prof, total = edit_profile(amp, rows)
    print(f"  热点总权重={total:.0f}, top位置:", prof.most_common(15))

debug_ref('NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls',
          'ref24013gene3', ['AAGTCTCGATCTAATTTACA','GAGAGGGTGGACGTCCAAAC'])
debug_ref('NEWdata/_旧数据_已在data中/USR-4411-SY2198/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls',
          'refABCgene1', ['GGCGTTAGATTGACAGAAGA'])
