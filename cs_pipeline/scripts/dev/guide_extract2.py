# -*- coding: utf-8 -*-
"""guide 提取 v2：缺失序列定位(强信号) + 小写标记(弱信号) 联合打分"""
import pandas as pd, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks
from guide_extract import merge_reads, map_positions

COMP = str.maketrans('ACGT','TGCA')
def rc(s): return s.translate(COMP)[::-1]

def assemble_ref(bl):
    amp=''
    for h in bl:
        amp = merge_reads(amp, str(h['header']['Left reads seq']))
        amp = merge_reads(amp, str(h['header']['Right reads seq']))
    wt=[v for b in bl for v in b['vars'] if v['Left variation type']=='WT' and v['Right variation type']=='WT']
    for v in (wt if wt else [v for b in bl for v in b['vars']]):
        amp = merge_reads(amp, str(v['Left reads seq']))
        amp = merge_reads(amp, str(v['Right reads seq']))
    return amp if len(amp)>=50 else None

def cut_evidence(amp, rows):
    """返回每个 amplicon 坐标上的 cut 证据权重"""
    from collections import Counter
    ev = Counter()
    for v in rows:
        if v['Left variation type']=='WT' and v['Right variation type']=='WT': continue
        try: rn = float(v['Reads number'])
        except Exception: rn = 1.0
        ltype, rtype = str(v['Left variation type']), str(v['Right variation type'])
        # 强信号：缺失序列跨越 cut
        for col in ('Left variation','Right variation'):
            dseq = str(v[col])
            if dseq in ('nan','-',''): continue
            for part in dseq.split(','):
                part = part.strip().upper()
                m = re.match(r'^([ACGT]+)(->([ACGT]))?$', part)
                if not m: continue
                if 'D' not in ltype+rtype: continue
                del_seq = m.group(1)
                if len(del_seq) < 1: continue
                i = amp.find(del_seq)
                if i < 0: continue
                # cut 应在缺失区间内及其 ±4
                for c in range(max(0,i-4), min(len(amp), i+len(del_seq)+4)):
                    ev[c] += rn * 3.0
        # 弱信号：小写标记位置附近
        for col in ('Left reads seq','Right reads seq'):
            seq = str(v[col])
            if seq in ('nan',''): continue
            low = [i for i,c in enumerate(seq) if c.islower() and c.upper() in 'ACGT']
            if not low: continue
            posmap = map_positions(amp, seq)
            for i in low:
                if i in posmap:
                    p = posmap[i]
                    for c in range(max(0,p-8), min(len(amp), p+5)):
                        ev[c] += rn
    return ev

def candidates(amp):
    """所有 NGG guide 候选: (cut_amp坐标, strand, guide, pam)"""
    out=[]
    L=len(amp)
    for a in range(0, L-23):
        g = amp[a:a+20]; pam = amp[a+20:a+23]
        if pam[1:]=='GG' and set(g+pam)<=set('ACGT'):
            out.append((a+17, '+', g, pam))
    r = rc(amp)
    for b in range(0, L-23):
        g = r[b:b+20]; pam = r[b+20:b+23]
        if pam[1:]=='GG' and set(g+pam)<=set('ACGT'):
            cut_amp = L-(b+17)
            out.append((cut_amp, '-', g, pam))
    return out

def pick_guides(amp, ev, max_guides=2):
    cands = candidates(amp)
    if not cands: return []
    scored = [(sum(v for p,v in ev.items() if abs(p-c)<=6), c, s, g, pam) for c,s,g,pam in cands]
    scored.sort(reverse=True)
    if not scored or scored[0][0]==0: return []
    picks=[scored[0]]
    if max_guides>1:
        for s in scored[1:]:
            if abs(s[1]-scored[0][1])>30 and s[0] >= 0.25*scored[0][0]:
                picks.append(s); break
    return picks  # [(weight, cut_amp, strand, guide, pam)]

if __name__=='__main__':
    master = pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet1')
    tests = [
      ('USR-25902','NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'),
      ('USR-23709','NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls'),
      ('USR-26162','NEWdata/_旧数据_已在data中/USR-26162-SY13345/整理后-2-T1+T2-all-SY13345-USR-26162-Hi-TOM-sequencing-result.xls'),
      ('USR-4411','NEWdata/_旧数据_已在data中/USR-4411-SY2198/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls'),
    ]
    tot_hit=tot_miss=0
    for batch,f in tests:
        d=load_hitom(f); blocks=split_blocks(d)
        refs={}
        for b in blocks: refs.setdefault(b['ref'],[]).append(b)
        truth = set(zip(master[master['batch']==batch]['seq-20'],
                        master[master['batch']==batch]['pam'],
                        master[master['batch']==batch]['strand']))
        print(f"\n===== {batch} 主表guide数={len(truth)} =====")
        for ref, bl in refs.items():
            amp = assemble_ref(bl)
            if not amp: print(f"  {ref}: [无序列]"); continue
            rows=[v for b in bl for v in b['vars']]
            ev = cut_evidence(amp, rows)
            picks = pick_guides(amp, ev)
            got = {(g,pam,s) for w,c,s,g,pam in picks}
            hits = got & truth
            miss = truth - got
            tot_hit += len(hits); tot_miss += len(miss)
            print(f"  {ref}: amp={len(amp)}bp")
            for w,c,s,g,pam in picks:
                tag='[命中]' if (g,pam,s) in truth else '[多余]'
                print(f"    {tag} {s} {g}+{pam} cut@{c} w={w:.0f}")
            for t in miss:
                inamp = (t[0] in amp) or (t[0] in rc(amp))
                print(f"    [漏提] {t[2]} {t[0]}+{t[1]}  (在amplicon中: {inamp})")
    print(f"\n总命中={tot_hit} 总漏提={tot_miss}")
