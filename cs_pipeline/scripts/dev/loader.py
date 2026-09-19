# -*- coding: utf-8 -*-
"""Hi-TOM 结果文件读取：自动识别 xls/xlsx/tsv，容忍首列空索引、行尾分隔符、\\r"""
import pandas as pd, re

COLS9 = ['Sort','Reads number','Ratio','Left variation type','Right variation type',
         'Left variation','Right variation','Left reads seq','Right reads seq']

def load_hitom(path):
    with open(path,'rb') as f: magic = f.read(8)
    if magic.startswith(b'\xd0\xcf\x11\xe0'):
        df = pd.read_excel(path, engine='xlrd')
    elif magic[:4] == b'PK\x03\x04':
        df = pd.read_excel(path, engine='openpyxl')
    else:
        df = None
        for enc in ('utf-8','gbk','gb18030'):
            try:
                with open(path, encoding=enc) as fh:
                    text = fh.read()
                df = text; break
            except Exception: continue
        if df is None: raise ValueError('unreadable: '+path)
        rows = []
        for ln in df.splitlines():
            parts = [p.strip() for p in ln.split('\t')]
            while parts and parts[-1] == '': parts.pop()
            if parts and parts[0] == '': parts = parts[1:]   # 去掉空索引列
            if not parts: continue
            if parts[0] == 'Sort': continue                  # 表头
            rows.append((parts + ['']*9)[:9])
        df = pd.DataFrame(rows, columns=COLS9)
    # 统一：去 Unnamed 列，规范列名
    df = df[[c for c in df.columns if not str(c).startswith('Unnamed')]]
    df.columns = [str(c).strip() for c in df.columns]
    for c in COLS9:
        if c not in df.columns: df[c] = pd.NA
    return df[COLS9].replace('', pd.NA)

def split_blocks(df):
    """返回 list of dict: {block, sample, ref, header, vars}"""
    blocks = []; cur = None
    for _, r in df.iterrows():
        s = str(r['Sort'])
        if re.match(r'^\d+-\S', s):
            cur = {'block': s, 'sample': s.split('-',1)[0], 'ref': s.split('-',1)[1],
                   'header': r, 'vars': []}
            blocks.append(cur)
        elif cur is not None:
            cur['vars'].append(r)
    return blocks
