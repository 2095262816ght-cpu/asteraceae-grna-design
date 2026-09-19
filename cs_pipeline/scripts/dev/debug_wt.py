# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks

d=load_hitom('NEWdata/02_HiTOM结果表格/USR-14333-SY7249/all-SY7249-USR-14333-Hi-TOM-sequencing-result.xls')
blocks=split_blocks(d)
b0=blocks[0]
print("block:", b0['block'], " vars数:", len(b0['vars']))
for v in b0['vars'][:3]:
    print("type:", v['Left variation type'], "|", v['Right variation type'],
          "| Lseq:", str(v['Left reads seq'])[:50], "| Rseq:", str(v['Right reads seq'])[:50])
# 找一个 WT 行
for b in blocks:
    for v in b['vars']:
        if v['Left variation type']=='WT' and v['Right variation type']=='WT':
            print("\nWT行示例 block", b['block'])
            print("Lseq:", str(v['Left reads seq'])[:80])
            print("Rseq:", str(v['Right reads seq'])[:80])
            sys.exit()
