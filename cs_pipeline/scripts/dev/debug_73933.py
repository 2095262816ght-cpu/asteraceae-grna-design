# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract2 import assemble_ref, rc

f='NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'
blocks=split_blocks(load_hitom(f))
bl=[b for b in blocks if b['ref']=='ref73933gene2']
print("73933 块数:", len(bl), " 块名:", [b['sample'] for b in bl])
amp=assemble_ref(bl)
print("amp:", amp)
for g in ['TATTCGCCAGGTGGACGATC','CCCCTGTTGATTCTGGATTC']:
    i=amp.find(g); j=rc(amp).find(g)
    print(f"guide {g}: 正向={i} 反向={j}" + (f" cut={i+17}" if i>=0 else "") + (f" rc中cut={j+17}->amp cut={len(amp)-(j+17)}" if j>=0 else ""))
# 第一个块的变异行
b0=bl[0]
print(f"\n=== block {b0['block']} ===")
for v in b0['vars']:
    print(f"{str(v['Sort']):>3} rn={v['Reads number']} ratio={v['Ratio']} {v['Left variation type']}/{v['Right variation type']} Lvar={v['Left variation']} Rvar={v['Right variation']}")
    print("    L:", str(v['Left reads seq']))
    print("    R:", str(v['Right reads seq']))
