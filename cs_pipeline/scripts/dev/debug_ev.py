# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract2 import assemble_ref, cut_evidence, candidates, rc

f='NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'
blocks=split_blocks(load_hitom(f))
bl=[b for b in blocks if b['ref']=='ref18265gene1']
amp=assemble_ref(bl)
print("amp:", len(amp))
print(amp)
g='CCAATCGCGAGAAAAAAAAG'
i=amp.find(g); print(f"\n真guide1 位置={i} cut={i+17} PAM={amp[i+20:i+23]}")
g2='GGACAATTTCAAATTAGGAG'
j=amp.find(g2); print(f"guide2 位置={j} cut={j+17} PAM={amp[j+20:j+23]}")
rows=[v for b in bl for v in b['vars']]
ev=cut_evidence(amp, rows)
top=ev.most_common(20)
print("\n证据top20:", sorted(top, key=lambda x:-x[1])[:20])
print(f"\n真guide1 cut={i+17} 窗口[±6]权重:", sum(v for p,v in ev.items() if abs(p-(i+17))<=6))
print(f"guide2 cut={j+17} 窗口权重:", sum(v for p,v in ev.items() if abs(p-(j+17))<=6))
