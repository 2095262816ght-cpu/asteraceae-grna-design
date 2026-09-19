# -*- coding: utf-8 -*-
"""QC 剔除标记: 对新表(17批)按块级三规则打 QC剔除 标记, 输出统计"""
import pandas as pd, re, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from loader import load_hitom, split_blocks

# 1. 计算每个块的 QC 判定
qc = {}   # (batch, block) -> (剔除?, 原因)
for f in sorted(glob.glob('NEWdata/02_HiTOM结果表格/*/*.xls')):
    batch = 'USR-' + re.search(r'USR-(\d+)', os.path.basename(os.path.dirname(f))).group(1)
    blocks = split_blocks(load_hitom(f))
    sums = []
    for b in blocks[:10]:
        s = 0.0
        for v in b['vars']:
            try: s += float(str(v['Ratio']).rstrip('%'))
            except Exception: pass
        if s > 0: sums.append(s)
    div = 100.0 if (sums and sum(sums)/len(sums) > 2) else 1.0
    for b in blocks:
        rows = []
        for v in b['vars']:
            try: r = float(str(v['Ratio']).rstrip('%')) / div
            except Exception: continue
            rows.append((r, str(v['Left variation type']), str(v['Right variation type'])))
        if not rows:
            qc[(batch, b['block'])] = (True, '无变异行'); continue
        is_wt = lambda lt, rt: lt == 'WT' and rt == 'WT'
        has_wt = any(is_wt(lt, rt) for _, lt, rt in rows)
        rows.sort(reverse=True)
        top1 = rows[0]
        if not has_wt:
            qc[(batch, b['block'])] = (True, '无WT行')
        elif not is_wt(top1[1], top1[2]) and top1[0] >= 0.8:
            qc[(batch, b['block'])] = (True, f'非WT主型{top1[0]*100:.0f}%≥80%')
        elif (len(rows) >= 2 and 0.35 <= rows[0][0] <= 0.65 and 0.35 <= rows[1][0] <= 0.65
              and not is_wt(rows[1][1], rows[1][2])):
            qc[(batch, b['block'])] = (True, '双峰40-60')
        else:
            qc[(batch, b['block'])] = (False, '')

# 2. 标记新表
NEW = 'data/1_Hi-results-13-NEWdata-20260918.xlsx'
d = pd.read_excel(NEW, sheet_name='Sheet1')
qc_sheet = pd.read_excel(NEW, sheet_name='guide候选')
doc_sheet = pd.read_excel(NEW, sheet_name='说明')
d['备注'] = d['备注'].fillna('')
n_mark = 0
for i, r in d.iterrows():
    mm = re.match(r'块(\S+?)[;；]', r['备注']) or re.match(r'块(\S+)$', r['备注'])
    if not mm: continue
    key = (r['batch'], mm.group(1))
    if key in qc and qc[key][0]:
        d.at[i, '备注'] = r['备注'] + f"; QC剔除({qc[key][1]})"
        n_mark += 1
with pd.ExcelWriter(NEW, engine='openpyxl') as w:
    d.to_excel(w, sheet_name='Sheet1', index=False)
    qc_sheet.to_excel(w, sheet_name='guide候选', index=False)
    doc_sheet.to_excel(w, sheet_name='说明', index=False)

# 3. 统计
print(f'QC剔除标记: {n_mark}/{len(d)} 行')
dd = d.copy(); dd['qc'] = dd['备注'].str.contains('QC剔除')
print(dd.groupby('batch')['qc'].agg(['sum','count']).to_string())
# 保存剔除清单
d[d['备注'].str.contains('QC剔除')][['guide-id','batch','备注']].to_csv('results/qc_excluded_0918.csv', index=False)
print('清单: results/qc_excluded_0918.csv')
