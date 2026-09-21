# -*- coding: utf-8 -*-
"""b_crosscheck_0921.py — 回传文件交叉核对（审计 C 项闭环）
① (4).xlsx 谱系；② 计B批注版备注裁决标签 vs excluded_gids_final_0919；
③ 用 guide候选表复推 15 版全部规则2/3/4分级（128 A/80 + 91 B/60 + 75 D/25）；
④ 16 版 22 行"待定"能否定级；⑤ 14→15 谱系。
运行: cd cs_pipeline && python scripts/dev/b_crosscheck_0921.py
"""
import re
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F4 = "data/1_Hi-results-13-merged-20260918(4).xlsx"
FANNO = "data/1_Hi-results-13-merged-20260918_计B批注版.xlsx"
F14 = "data/1_Hi-results-14-scoring-20260920.xlsx"
F15 = "data/1_Hi-results-15-efficiency-20260920.xlsx"
F16 = "data/1_Hi-results-16-efficiency-20260921.xlsx"
EXCL_CSV = "results/excluded_gids_final_0919.csv"

excl = set(pd.read_csv(EXCL_CSV)["guide-id"].astype(str))
anno = pd.read_excel(FANNO, "Sheet1")
repo = pd.read_excel("data/1_Hi-results-13-merged-20260918.xlsx", "Sheet1")
g15 = pd.read_excel(F15, "全部打分")
g16 = pd.read_excel(F16, "全部打分")
cand = pd.read_excel(FANNO, "guide候选")

print("== ① (4).xlsx ==")
print("   与仓库13-merged字节级相同(md5一致) → 纯重复下载副本，无老师批注；'老师批注版'标签名不符实")

print("\n== ② 批注版备注裁决标签 vs EXCL-360 ==")
note_a = anno["备注"].fillna("").astype(str)
gid_a = anno["guide-id"].astype(str)
tag_batch = note_a.str.contains("整批剔除(9.19裁决", regex=False)
tag_qc_rev = note_a.str.contains("QC撤销", regex=False) | note_a.str.contains("6137保留", regex=False) | note_a.str.contains("杂合子", regex=False)
print("   含'整批剔除(9.19裁决'标签:", int(tag_batch.sum()), "行, 批次:",
      anno.loc[tag_batch, "batch"].value_counts().to_dict())
print("   含QC撤销类标签:", int(tag_qc_rev.sum()), "行, 批次:", anno.loc[tag_qc_rev, "batch"].value_counts().to_dict())
# 14333/22807 全体是否都在 EXCL
b14333 = set(gid_a[anno["batch"] == "USR-14333"])
b22807 = set(gid_a[anno["batch"] == "USR-22807"])
print("   USR-14333 %d行 全在EXCL: %s | USR-22807 %d行 全在EXCL: %s"
      % (len(b14333), b14333 <= excl, len(b22807), b22807 <= excl))
# EXCL 中非 QC 备注且非整批的行 = ?
g15note = g15["备注"].fillna("").astype(str)
g15gid = g15["guide-id"].astype(str)
in_ex = g15gid.isin(excl)
qc15 = g15note.str.contains("QC剔除") | g15note.str.contains("整批剔除") | g15note.str.contains("非NGG")
print("   EXCL行中15版备注无QC/整批标记的:", int((in_ex & ~qc15).sum()),
      sorted(g15gid[in_ex & ~qc15])[:10])
# 批注版标签行 vs EXCL 差集
anno_tag = set(gid_a[tag_batch])
print("   '整批剔除'标签行 ⊆ EXCL:", anno_tag <= excl, "| EXCL∩(14333∪22807) 未带标签行:",
      len((b14333 | b22807) & excl - anno_tag))
# 6137 的 80 行仓库版更长 —— 批注版把备注改成了什么？
d6137 = (note_a != repo["备注"].fillna("").astype(str)) & (anno["batch"] == "USR-6137")
print("   USR-6137 备注被改行:", int(d6137.sum()), "样例:")
for i in anno.index[d6137][:4]:
    print("     ", anno.loc[i, "guide-id"])
    print("       批注版:", str(anno.loc[i, "备注"])[:150])
    print("       仓库版:", str(repo.loc[i, "备注"])[:150])
qc_removed = d6137 & repo["备注"].fillna("").astype(str).str.contains("QC剔除") & ~note_a.str.contains("QC剔除")
print("   6137 中'QC剔除'字样被移除的行:", int(qc_removed.sum()))

print("\n== ③ guide候选表复推 15 版规则2/3/4 ==")
print("   guide候选: %d 条, %d 个ref, 列=%s" % (len(cand), cand["ref"].nunique(), list(cand.columns)))
cand_by_ref = {str(r): grp.sort_values("热点得分", ascending=False) for r, grp in cand.groupby("ref")}
cand_by_ref.update({str(r)[3:]: v for r, v in cand_by_ref.items() if str(r).startswith("ref")})
cand_by_ref.update({str(k).lower(): v for k, v in list(cand_by_ref.items())})

def ref_lookup(ref):
    if ref is None:
        return None
    c = cand_by_ref.get(ref)
    if c is None:
        c = cand_by_ref.get(str(ref).lower())
    return c

def ref_of(note: str):
    m = re.search(r"块\d+-ref([A-Za-z0-9]+)", note)
    return m.group(1) if m else None

def rule_of(top1, top2):
    if top1 < 100:
        return "D"
    if top1 >= 500 and (top2 == 0 or top1 >= 4 * top2):
        return "A"
    return "B"

sub = g15[g15["备注"].fillna("").astype(str).str.contains("待设计表确认")].copy()
sub["ref"] = sub["备注"].astype(str).map(ref_of)
rows = []
for _, r in sub.iterrows():
    ref = r["ref"]
    c = ref_lookup(ref)
    if c is None:
        rows.append((r["guide-id"], ref, None, None, None, "ref不在候选表"))
        continue
    top1 = float(c["热点得分"].iloc[0])
    top2 = float(c["热点得分"].iloc[1]) if len(c) > 1 else 0.0
    rows.append((r["guide-id"], ref, top1, top2, rule_of(top1, top2), "ok"))
chk = pd.DataFrame(rows, columns=["guide-id", "ref", "top1", "top2", "复推等级", "状态"])
m = sub.drop(columns=["ref"]).merge(chk, on="guide-id")
print("   待设计表确认行:", len(m), "| ref缺失:", int((m['状态'] != 'ok').sum()),
      sorted(m.loc[m['状态'] != 'ok', 'ref'].unique())[:10])
ok = m[m["状态"] == "ok"].copy()
# 15版给的等级：QC剔除行(rule1优先)不参与——只看非剔除行
ok_nq = ok[ok["处理状态"] == "保留"]
agree = (ok_nq["复推等级"] == ok_nq["等级"])
print("   非剔除行 %d: 复推一致 %d, 不一致 %d" % (len(ok_nq), agree.sum(), (~agree).sum()))
if (~agree).sum():
    print(ok_nq[~agree][["guide-id", "ref", "top1", "top2", "等级", "复推等级", "判定依据"]].head(15).to_string())
print("   按15版等级 x 复推等级:")
print(pd.crosstab(ok_nq["等级"], ok_nq["复推等级"]).to_string())
# 判定依据里引用的分数 vs 候选表
cited = ok["判定依据"].astype(str).str.extract(r"Top1得分(\d+)").astype(float).iloc[:, 0]
hasc = cited.notna()
mism = ok[hasc & (cited[hasc] != ok.loc[hasc, "top1"])]
print("   判定依据引用Top1分数与候选表不符:", len(mism))
# QC剔除的待确认行(173)复推等级分布（仅参考）
ok_q = ok[ok["处理状态"] == "剔除"]
print("   QC剔除的待确认行 %d, 复推等级分布(参考): %s" % (len(ok_q), ok_q["复推等级"].value_counts().to_dict()))

print("\n== ④ 16版22行'待定'定级 ==")
pend = g16[(g16["等级"] == "待定") & (g16["处理状态"] == "保留")].copy()
pend["ref"] = pend["备注"].astype(str).map(ref_of)
print("   待定保留行:", len(pend), "refs:", pend["ref"].value_counts().to_dict())
res = []
for _, r in pend.iterrows():
    c = ref_lookup(r["ref"])
    if c is None:
        res.append((r["guide-id"], r["ref"], None, None, "ref缺"))
        continue
    top1 = float(c["热点得分"].iloc[0])
    top2 = float(c["热点得分"].iloc[1]) if len(c) > 1 else 0.0
    res.append((r["guide-id"], r["ref"], top1, top2, rule_of(top1, top2)))
pr = pd.DataFrame(res, columns=["guide-id", "ref", "top1", "top2", "应定级"])
print(pr.to_string())
print("   应定级分布:", pr["应定级"].value_counts().to_dict())
# 待定行当前 seq-20 是否等于该 ref 的 Top1 候选
pend2 = pend.merge(pr.drop(columns=["ref"]), on="guide-id")
for _, r in pend2[pend2["应定级"].isin(["A", "B"])].iterrows():
    c = ref_lookup(r["ref"])
    top_seq = c["seq20"].iloc[0]
    same = str(r["seq-20"]) == str(top_seq)
    if not same:
        print("   !! %s seq-20=%s ≠ ref%s Top1候选=%s" % (r["guide-id"], r["seq-20"], r["ref"], top_seq))

print("\n== ⑤ 14→15 谱系 ==")
a14 = pd.read_excel(F14, "全部打分")
print("   14版 cols:", list(a14.columns))
c15 = list(g15.columns)
print("   15版前18列==14版列:", c15[:18] == list(a14.columns))
if c15[:18] == list(a14.columns):
    diffs = 0
    for col in a14.columns:
        x, y = a14[col].astype(str), g15[col].astype(str)
        diffs += int((x != y).sum())
    print("   共同18列 cell diffs (14 vs 15):", diffs)
for sh in ["训练集", "剔除清单"]:
    x14, x15 = pd.read_excel(F14, sh), pd.read_excel(F15, sh)
    print(f"   [{sh}] 14版{x14.shape} vs 15版{x15.shape}, guide-id集合相同:",
          set(x14['guide-id']) == set(x15['guide-id']))
