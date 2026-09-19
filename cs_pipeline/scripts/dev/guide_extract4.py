# -*- coding: utf-8 -*-
"""guide 提取 v4：PAM 几何约束
规则（Cas9 编辑几何）:
- 编辑只发生在 protospacer 内（cut 上游），PAM 及其下游必须干净
- 缺失的 3' 端不能超过 cut（cut 在缺失末端下游 0-12bp）
- mark 不能落在 [c+3, c+8]（PAM 区）
"""
import pandas as pd, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads, map_positions
from guide_extract2 import assemble_ref, rc

def collect_evidence(amp, rows):
    """marks=[(pos,w)], dels=[(d0,d1,w)]  amp 坐标"""
    marks=[]; dels=[]
    for v in rows:
        lt, rt = str(v['Left variation type']), str(v['Right variation type'])
        if lt=='WT' and rt=='WT': continue
        if 'Large_Indel' in lt+rt: continue
        try: rn=float(v['Reads number'])
        except Exception: rn=1.0
        if 'D' in lt+rt:
            done=False
            for col in ('Left variation','Right variation'):
                if done: break
                for part in str(v[col]).split(','):
                    part=part.strip().upper()
                    if not re.fullmatch(r'[ACGT]{1,30}', part): continue
                    i=amp.find(part)
                    if i>=0 and amp.rfind(part)==i:
                        dels.append((i, i+len(part), rn)); done=True; break
        for col in ('Left reads seq','Right reads seq'):
            seq=str(v[col])
            if seq in ('nan',''): continue
            low=[i for i,c in enumerate(seq) if c.islower() and c.upper() in 'ACGT'
                 and 8<=i<len(seq)-8]
            if not low: continue
            posmap=map_positions(amp, seq)
            for i in low:
                if i in posmap: marks.append((posmap[i], rn))
    return marks, dels

def score_candidate(c, marks, dels):
    """'+' 坐标系下的候选 cut=c 打分"""
    s=0.0
    for p,w in marks:
        if c-20<=p<=c+2: s += w/(1.0+abs(p-(c-3)))
        elif c+3<=p<=c+8: s -= 3.0*w
    for d0,d1,w in dels:
        if d1<=c+2 and d0>=c-25:           # 缺失在 protospacer 内、3'端不越切点
            s += 3.0*w/(1.0+abs((d1-1)-(c-3))/3.0)
        elif d1>c+2:                        # 缺失越过切点进入 PAM 下游 → 非该 guide
            s -= 3.0*w
    return s

def pick_guides(amp, marks, dels, max_guides=2):
    L=len(amp)
    cands=[]
    for a in range(0, L-23):
        g=amp[a:a+20]; pam=amp[a+20:a+23]
        if pam[1:]=='GG' and set(g)<=set('ACGT'):
            cands.append((a+17,'+',g,pam))
    r=rc(amp)
    for b in range(0, L-23):
        g=r[b:b+20]; pam=r[b+20:b+23]
        if pam[1:]=='GG' and set(g)<=set('ACGT'):
            cands.append((L-(b+17),'-',g,pam))   # cut 换算回 amp 坐标
    if not cands: return []
    # '-' 候选在 rc 坐标系下打分
    def sc(c, strand):
        if strand=='+':
            return score_candidate(c, marks, dels)
        Lm=[(L-1-p,w) for p,w in marks]
        Ld=[(L-d1, L-d0, w) for d0,d1,w in dels]
        return score_candidate(L-c, Lm, Ld)
    scored=sorted(((sc(c,s), c, s, g, pam) for c,s,g,pam in cands), reverse=True)
    if scored[0][0]<=0: return []
    picks=[scored[0]]
    for s_ in scored[1:]:
        if abs(s_[1]-scored[0][1])>15 and s_[0]>=0.25*scored[0][0]:
            picks.append(s_)
            if len(picks)>=max_guides: break
    return picks

if __name__=='__main__':
    master=pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet1')
    tests=[
      ('USR-25902','NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'),
      ('USR-23709','NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls'),
      ('USR-4411','NEWdata/_旧数据_已在data中/USR-4411-SY2198/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls'),
    ]
    th=tx=tm=0
    for batch,f in tests:
        blocks=split_blocks(load_hitom(f))
        refs={}
        for b in blocks: refs.setdefault(b['ref'],[]).append(b)
        m=master[master['batch']==batch]
        truth_all=set(zip(m['seq-20'],m['pam']))
        print(f"\n===== {batch} =====")
        for ref,bl in refs.items():
            amp=assemble_ref(bl)
            if not amp: print(f"  {ref}: [无序列]"); continue
            rows=[v for b in bl for v in b['vars']]
            marks,dels=collect_evidence(amp,rows)
            picks=pick_guides(amp,marks,dels)
            truth={(g,p) for g,p in truth_all if g in amp or rc(g) in amp}
            got=set()
            line=[]
            for w,c,s,g,pam in picks:
                ok=(g,pam) in truth or (rc(g),rc(pam)) in truth
                got.add((g,pam))
                if ok: th+=1; tag='HIT'
                else: tx+=1; tag='X  '
                line.append(f"{tag} {s} {g}+{pam}@{c}({w:.0f})")
            for g,p in truth:
                if (g,p) not in got and (rc(g),rc(p)) not in got:
                    tm+=1; line.append(f"MISS {g}+{p}")
            print(f"  {ref}: "+" | ".join(line) if line else f"  {ref}: 无候选")
    print(f"\n命中={th} 多余={tx} 漏提={tm}")
