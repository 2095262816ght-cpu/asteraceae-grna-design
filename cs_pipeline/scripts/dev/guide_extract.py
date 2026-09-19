# -*- coding: utf-8 -*-
"""从 Hi-TOM 原始结果提取 guide+PAM：amplicon 拼装 + 编辑热点定位"""
import pandas as pd, re, sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loader import load_hitom, split_blocks
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def merge_reads(left, right):
    """overlap-merge 两条 reads 为 amplicon（双向：可向右延伸也可向左补前缀）"""
    left, right = str(left).upper(), str(right).upper()
    if left in ('NAN','NONE',''): return right
    if right in ('NAN','NONE',''): return left
    if len(left) < 10 or len(right) < 10:
        return left if len(left) >= len(right) else right
    best = 0
    for k in range(min(len(left),len(right)), 9, -1):
        if left[-k:] == right[:k]:
            best = k; break
    if best: return left + right[best:]
    for k in range(min(len(left),len(right)), 9, -1):
        if right[-k:] == left[:k]:
            return right + left[k:]
    if right in left: return left
    if left in right: return right
    return left  # 拼不上就用 left

def map_positions(ref, read):
    """用 difflib 把 read 的坐标映射到 ref 坐标，返回 dict read_idx->ref_idx"""
    import difflib
    sm = difflib.SequenceMatcher(None, ref, read.upper(), autojunk=False)
    m = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('equal','replace'):
            n = min(i2-i1, j2-j1)
            for t in range(n):
                m[j1+t] = i1+t
    return m

def edit_profile(ref, variant_rows):
    """返回 (reads加权的热点位置列表, 总权重)"""
    from collections import Counter
    prof = Counter(); total = 0
    for v in variant_rows:
        if v['Left variation type']=='WT' and v['Right variation type']=='WT': continue
        try: rn = float(v['Reads number'])
        except Exception: rn = 1.0
        for col in ('Left reads seq','Right reads seq'):
            seq = str(v[col])
            if seq in ('nan',''): continue
            low = [i for i,c in enumerate(seq) if c.islower() and c.upper() in 'ACGT']
            if not low: continue
            posmap = map_positions(ref, seq)
            for i in low:
                if i in posmap:
                    prof[posmap[i]] += rn; total += rn
    return prof, total

def find_guides(amplicon, prof, total, max_guides=2):
    """在 amplicon 正/反链找 cut 热点附近的 NGG guide"""
    comp = str.maketrans('ACGT','TGCA')
    cands = []
    for strand, seq in (('+', amplicon), ('-', amplicon.translate(comp)[::-1])):
        L = len(seq)
        for c in range(17, L-6):  # cut 在 c-1|c 之间; guide=[c-17,c+3), pam=[c+3,c+6)
            pam = seq[c+3:c+6]
            if len(pam)==3 and pam[1:]=='GG' and pam[0] in 'ACGT':
                guide = seq[c-17:c+3]
                w = sum(v for p,v in prof.items() if strand=='+' and c-8<=p<=c+2)
                if strand=='-':
                    w = sum(v for p,v in prof.items() if (L-1-(c+2))<=p<=(L-1-(c-8)))
                cands.append((w, strand, guide, pam, c if strand=='+' else L-c))
    cands.sort(reverse=True)
    if not cands: return []
    best = cands[0]
    if best[0]==0: return []  # 热点无支持
    guides=[best]
    # 检查是否有第二个独立热点（距第一 cut >30bp 且权重占比>25%）
    if max_guides>1 and total>0:
        for c in cands[1:]:
            if abs(c[4]-best[4])>30 and c[0]>0.25*best[0]:
                guides.append(c); break
    return guides

def process_ref(variant_rows_all):
    """输入某 ref 所有 block 的变异行，返回 (amplicon, guides)"""
    # 用 WT 行拼 amplicon
    wt = [v for v in variant_rows_all if v['Left variation type']=='WT' and v['Right variation type']=='WT']
    src = wt if wt else variant_rows_all
    amp = ''
    for v in src:
        amp = merge_reads(amp, str(v['Left reads seq']))
        amp = merge_reads(amp, str(v['Right reads seq']))
        if len(amp)>150: break
    if not amp: return None, []
    prof, total = edit_profile(amp, variant_rows_all)
    guides = find_guides(amp, prof, total)
    return amp, guides

if __name__=='__main__':
    # === 在旧批次上验证 ===
    master = pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet1')
    tests = [
      ('USR-25902','NEWdata/_旧数据_已在data中/USR-25902-SY13249-2024.8.28/all-SY13249-USR-25902-Hi-TOM-sequencing-result.xls'),
      ('USR-23709','NEWdata/_旧数据_已在data中/USR-23709-SY12100-2024.6.29/all-SY12100-USR-23709-Hi-TOM-sequencing-result.xls'),
      ('USR-26162','NEWdata/_旧数据_已在data中/USR-26162-SY13345/整理后-2-T1+T2-all-SY13345-USR-26162-Hi-TOM-sequencing-result.xls'),
      ('USR-4411','NEWdata/_旧数据_已在data中/USR-4411-SY2198/all-SY2198-USR-4411-Hi-TOM-sequencing-result.xls'),
    ]
    for batch,f in tests:
        d = load_hitom(f)
        blocks = split_blocks(d)
        refs = {}
        for b in blocks: refs.setdefault(b['ref'],[]).extend(b['vars'])
        truth = master[master['batch']==batch].groupby(['seq-20','pam','strand']).size().to_dict()
        print(f"\n===== {batch}  主表guide数={len(truth)} =====")
        for ref, rows in refs.items():
            amp, guides = process_ref(rows)
            if amp is None:
                print(f"  {ref}: [无可用序列]"); continue
            got = {(g[2],g[3],g[1]) for g in guides}
            print(f"  {ref}: amplicon={len(amp)}bp 提取{len(guides)}个guide")
            for g in guides:
                inm = (g[2],g[3],g[1]) in truth
                print(f"    -> {g[1]} {g[2]}+{g[3]}  热点权重={g[0]:.0f}  {'[主表命中]' if inm else '[主表无]'}")
