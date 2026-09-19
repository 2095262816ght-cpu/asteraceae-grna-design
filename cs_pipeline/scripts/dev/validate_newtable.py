# -*- coding: utf-8 -*-
"""新表全面质检"""
import pandas as pd, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

NEW='data/1_Hi-results-13-NEWdata-20260918.xlsx'
OLD='data/1_Hi-results-12-20260913.xlsx'
d=pd.read_excel(NEW, sheet_name='Sheet1')
m=pd.read_excel(OLD, sheet_name='Sheet1')
issues=[]

# 1. 结构
assert list(d.columns)==list(m.columns), '列不一致'
print(f"[1] 列结构一致: {list(d.columns)}")

# 2. guide-id 唯一、连续、不与主表冲突
assert d['guide-id'].is_unique, 'guide-id 重复'
overlap = set(d['guide-id']) & set(m['guide-id'])
assert not overlap, f'与主表 guide-id 冲突: {overlap}'
print(f"[2] guide-id 唯一且无冲突: {d['guide-id'].iloc[0]}..{d['guide-id'].iloc[-1]} 共{len(d)}")

# 3. seq20/pam 合法性
bad_seq = d[d['seq-20'].notna() & ~d['seq-20'].str.fullmatch(r'[ACGT]{20}', na=False)]
bad_pam = d[d['pam'].notna() & ~d['pam'].str.fullmatch(r'[ACGT]GG', na=False)]
print(f"[3] seq-20 非法行: {len(bad_seq)}, pam 非NGG行: {len(bad_pam)}")
if len(bad_seq): issues.append(('seq20非法', bad_seq['guide-id'].tolist()))

# 4. indel_pct 范围
bad_indel = d[(d['indel_pct']<0)|(d['indel_pct']>1)]
print(f"[4] indel_pct 越界行: {len(bad_indel)}, 缺失: {int(d['indel_pct'].isna().sum())}")

# 5. 坐标与基因组一致性全量复核 (TKS genome)
def load_genome(path):
    seqs={}; name=None; buf=[]
    with open(path) as f:
        for ln in f:
            if ln.startswith('>'):
                if name: seqs[name]=''.join(buf).upper()
                name=ln[1:].split()[0]; buf=[]
            else: buf.append(ln.strip())
    if name: seqs[name]=''.join(buf).upper()
    return seqs
comp=str.maketrans('ACGT','TGCA')
rc=lambda s: s.translate(comp)[::-1]
G=load_genome('data/reference_genomes/2-1_TKS.genome.fasta')
ok=fail=0; fails=[]
for _,r in d[d['seq-20'].notna()].iterrows():
    chrom=str(r['chrom']); s=int(r['start']); e=int(r['end'])
    seg=G[chrom][s-1:e-1]  # start 1-based, end=start+20 (开区间)
    if seg==r['seq-20'] or rc(seg)==r['seq-20']: ok+=1
    else: fail+=1; fails.append((r['guide-id'], r['seq-20'], seg))
print(f"[5] 基因组坐标复核: {ok} 通过, {fail} 失败")
for x in fails[:5]: print('    FAIL:', x)

# 6. PAM 与基因组一致性 (按原型链向验证: 候选表里的方向)
qc=pd.read_excel(NEW, sheet_name='guide候选')
pam_ok=pam_fail=0
for _,r in qc[qc['seq20'].notna()].iterrows():
    mm2=re.match(r'(LG\d+):(\d+)-(\d+)', str(r['基因组坐标']))
    if not mm2: continue
    chrom,s,e=mm2.group(1),int(mm2.group(2)),int(mm2.group(3))
    if r['原型链向']=='+':
        pam=G[chrom][e-1:e+2]  # 20bp 之后 3bp (e 为 1-based 开区间末)
    else:
        pam=rc(G[chrom][s-4:s-1])
    if pam==r['pam']: pam_ok+=1
    else: pam_fail+=1; print('    PAM不符:', r['ref'], r['seq20'], r['pam'], '基因组实际:', pam)
print(f"[6] 候选表 PAM 基因组复核: {pam_ok} 通过, {pam_fail} 失败")

# 7. 与主表的 (seq20, batch) 重复检查
d['uid']=d['seq-20'].astype(str)+'__'+d['batch'].astype(str)
m2=m.copy(); m2['uid']=m2['seq-20'].astype(str)+'__'+m2['batch'].astype(str)
dup=set(d['uid'])&set(m2['uid'])
print(f"[7] 与主表 (seq20,batch) 重复: {len(dup)}")

# 8. 每个 batch 的块数与原始文件对账
import glob
from loader import load_hitom, split_blocks
batch_blocks = {}
for f in sorted(glob.glob('NEWdata/02_HiTOM结果表格/*/*.xls')):
    blocks = split_blocks(load_hitom(f))
    batch = re.search(r'USR-(\d+)', os.path.basename(os.path.dirname(f))).group(1)
    batch_blocks[f'USR-{batch}'] = batch_blocks.get(f'USR-{batch}', 0) + len(blocks)

all_match = True
for batch, raw_count in sorted(batch_blocks.items()):
    n_new = len(d[d['batch']==batch])
    ok = (raw_count == n_new)
    if not ok: all_match = False
    print(f"    {batch}: 原始块={raw_count} 新表行={n_new} {'✓' if ok else '✗'}")
assert all_match, '存在原始块数与新表行数不一致的批次'
print(f"[8] 块数对账全部通过")

print("\n=== 总结 ===")
print("问题:", issues if issues else "无结构性问题")
