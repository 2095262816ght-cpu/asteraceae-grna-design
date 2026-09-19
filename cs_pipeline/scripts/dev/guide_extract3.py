# -*- coding: utf-8 -*-
"""guide 提取 v3：距离衰减打分 + 缺失跨切点强信号 + 链向无关验证"""
import pandas as pd, re, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads, map_positions
from guide_extract2 import assemble_ref, candidates, rc

def cut_evidence(amp, rows):
    """返回 [(pos, weight)] 证据列表"""
    ev = []
    for v in rows:
        lt, rt = str(v['Left variation type']), str(v['Right variation type'])
        if lt=='WT' and rt=='WT': continue
        if 'Large_Indel' in lt+rt: continue
        try: rn = float(v['Reads number'])
        except Exception: rn = 1.0
        # 强信号：缺失序列必须跨切点
        if 'D' in lt+rt:
            for col in ('Left variation','Right variation'):
                for part in str(v[col]).split(','):
                    part = part.strip().upper()
                    if not re.fullmatch(r'[ACGT]{1,30}', part): continue
                    i = amp.find(part)
                    if i < 0 or amp.rfind(part) != i: continue   # 要求唯一匹配
                    for c in range(i, i+len(part)):
                        ev.append((c, rn*3.0))
                    break  # 左右两列通常相同，只计一次
        # 弱信号：小写标记（排除 read 两端 8bp 防比对伪影）
        for col in ('Left reads seq','Right reads seq'):
            seq = str(v[col])
            if seq in ('nan',''): continue
            low = [i for i,c in enumerate(seq) if c.islower() and c.upper() in 'ACGT'
                   and 8 <= i < len(seq)-8]
            if not low: continue
            posmap = map_positions(amp, seq)
            for i in low:
                if i in posmap: ev.append((posmap[i], rn))
    return ev

def pick_guides(amp, ev, max_guides=2):
    cands = candidates(amp)
    if not cands or not ev: return []
    def score(c):
        return sum(w/(1.0+abs(p-c)) for p,w in ev)
    scored = sorted(((score(c), c, s, g, pam) for c,s,g,pam in cands), reverse=True)
    if scored[0][0]==0: return []
    picks=[scored[0]]
    for s in scored[1:]:
        if abs(s[1]-scored[0][1])>15 and s[0] >= 0.25*scored[0][0]:
            picks.append(s)
            if len(picks)>=max_guides: break
    return picks

if __name__=='__main__':
    master = pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet1')
    tests = [
      ('USR-25902','NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'),
      ('USR-23709','NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls'),
      ('USR-4411','NEWdata/_旧数据_已在data中/USR-4411-SY2198/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls'),
    ]
    tot_h=tot_m=tot_x=0
    for batch,f in tests:
        d=load_hitom(f); blocks=split_blocks(d)
        refs={}
        for b in blocks: refs.setdefault(b['ref'],[]).append(b)
        m = master[master['batch']==batch]
        truth_all = set(zip(m['seq-20'], m['pam']))
        print(f"\n===== {batch} =====")
        for ref, bl in refs.items():
            amp = assemble_ref(bl)
            if not amp: print(f"  {ref}: [无序列]"); continue
            rows=[v for b in bl for v in b['vars']]
            ev = cut_evidence(amp, rows)
            picks = pick_guides(amp, ev)
            # 该 ref 的标准答案 = 主表中落在本 amplicon 里的 guide（链向归一化）
            truth = set()
            for g,pam in truth_all:
                if g in amp or rc(g) in amp: truth.add((g,pam))
            got=set()
            for w,c,s,g,pam in picks:
                hit = (g,pam) in truth or (rc(g),rc(pam)) in truth
                got.add((g,pam))
                tag='[命中]' if (g,pam) in truth else ('[命中-rc]' if (rc(g),rc(pam)) in truth else '[多余]')
                if tag!='[多余]': tot_h+=1
                else: tot_x+=1
                print(f"    {tag} {s} {g}+{pam} cut@{c} score={w:.0f}")
            for g,pam in truth:
                if (g,pam) not in got and (rc(g),rc(pam)) not in got:
                    tot_m+=1
                    print(f"    [漏提] {g}+{pam}")
    print(f"\n命中={tot_h} 多余={tot_x} 漏提={tot_m}")
