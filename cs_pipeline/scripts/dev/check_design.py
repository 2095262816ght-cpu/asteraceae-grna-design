# -*- coding: utf-8 -*-
import pandas as pd, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 新 ref 的基因组位点
loci = {
 'refsm1':('LG05',110992805,110992959),'refABCM1':('LG05',110992805,110992959),
 'refABCM2':('LG05',110992481,110992642),
 'ref1661':('LG05',122559236,122559428),'ref1662':('LG05',122559905,122560079),
 'ref1841':('LG06',28385640,28385800),'ref1842':('LG06',28385189,28385340),
 'refQYJ':('LG05',80325443,80325632),
 'refHiTom5':('LG05',89620799,89620975),'refHiTom3':('LG03',6490051,6490268),
 'refCALB1':('LG03',9963933,9964070),'refCALB2':('LG03',9958139,9958262),
 'ref22B1':('LG05',89620912,89621118),'ref23B34':('LG03',6490794,6490917),
 'ref22B23':('LG05',89620830,89621011),'ref23B12':('LG03',6490081,6490204),
 'ref22B18':('LG05',89620799,89620975),
 'ref05nB5':('LG05',89619740,89619958),'ref05nB7nB8':('LG05',89618142,89618284),
 'ref05nB6':('LG05',89618412,89618542),
 'refSP3':('LG07',109029032,109029136),'refABC49261':('LG05',97239167,97239297),
}
for f in ['data/hitom/hitom_all_307_to_fill.csv','data/hitom/hitom_seq30_full_0916.csv','data/hitom/hitom_clean_full_0916.csv']:
    d=pd.read_csv(f)
    print(f"--- {f} ({len(d)}行) ---")
    any_hit=False
    for ref,(ch,s,e) in loci.items():
        d['start']=pd.to_numeric(d['start'],errors='coerce'); sub=d[(d['chrom']==ch)&(d['start']>=s-500)&(d['start']<=e+500)]
        for _,r in sub.iterrows():
            print(f"  {ref} 位点附近: {r.get('guide_id','?')} {r.get('seq20','?')}+{r.get('pam','?')} {ch}:{r['start']}")
            any_hit=True
    if not any_hit: print("  无命中")

# 主表 Sheet2 设计位点表
x=pd.read_excel('data/1_Hi-results-12-20260913.xlsx', sheet_name='Sheet2', header=None)
print("\n=== 主表 Sheet2 全文 ===")
print(x.to_string())
