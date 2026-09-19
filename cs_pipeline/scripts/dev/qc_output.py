# -*- coding: utf-8 -*-
import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
pd.set_option('display.width',250); pd.set_option('display.max_columns',30); pd.set_option('display.max_colwidth',40)

f='data/1_Hi-results-13-NEWdata-20260918.xlsx'
d=pd.read_excel(f, sheet_name='Sheet1')
qc=pd.read_excel(f, sheet_name='guide候选')

print("=== 高置信行抽查 (应对齐主表坐标) ===")
print(d[d['备注'].str.contains('guide确定')].groupby(['gene-id','seq-20','pam','chrom','start','end','strand']).size().to_string())
print("\n主表对照: LG05.2725=LG05:110992938-110992958(-), LG05.2111=LG05:97239224-97239244(+), LG07.3296=LG07:109029054-109029074(-)")

print("\n=== 各 ref 的基因归属 ===")
print(qc[['ref','gene-id','结论']].drop_duplicates().to_string(index=False))

print("\n=== guide未确定的行 ===")
print(d[d['备注'].str.contains('未确定')].groupby(['batch']).size().to_string())

print("\n=== 警告行 (无WT/占比异常) ===")
warn=d[d['备注'].str.contains('无WT|≠100|无变异')]
print(warn[['guide-id','batch','indel_pct','备注']].head(20).to_string(index=False))
print("警告行总数:", len(warn))

print("\n=== indel_pct 分布 ===")
print(d['indel_pct'].describe().to_string())
