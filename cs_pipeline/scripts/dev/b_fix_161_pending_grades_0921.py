# -*- coding: utf-8 -*-
"""b_fix_161_pending_grades_0921.py — 16.1 版：guide候选表回传后补完 22 行"待定"分级

输入: data/1_Hi-results-16-efficiency-20260921.xlsx（全部打分 sheet）
      data/1_Hi-results-13-merged-20260918_计B批注版.xlsx（guide候选 sheet, 61条/35ref）
规则: 与 15 版打分规则 2/3/4 完全一致（b_crosscheck_0921.py 已对 219 行复推 100% 验证）
  Top1≥500 且 ≥4×次选 → A/80；Top1 100~500 或差距<4倍 → B/60；Top1<100 → D/25 弱信号
结果: 16 行 refM(Top1=68077,次选0) → A/80 保留；6 行 refSP1(Top1=62) → D/25 移入 剔除(弱信号,待老师追认)
口径: 1368 = 保留969(训练集) + 保留-不可打分3 + 剔除(9.19裁决)360 + 剔除(弱信号,待追认)36
      训练集969 + 弱信号36 = 1005 = 9.19裁决保留的可打分行数（与 b_anchor_final_0919 口径一致）
效率分: 综合分/排名在 969 行内重算（纯百分位、并列同名次，同 16 版 B1 修复口径）
输出: data/1_Hi-results-16.1-efficiency-20260921.xlsx
运行: cd cs_pipeline && python scripts/dev/b_fix_161_pending_grades_0921.py
"""
import re
import sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata, pearsonr, spearmanr

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "data/1_Hi-results-16-efficiency-20260921.xlsx"
ANNO = "data/1_Hi-results-13-merged-20260918_计B批注版.xlsx"
OUT = "data/1_Hi-results-16.1-efficiency-20260921.xlsx"

ST_KEEP = "保留"
ST_KEEP_NS = "保留(不可打分,待复核)"
ST_EXCL_RULING = "剔除(9.19裁决)"
ST_EXCL_WEAK = "剔除(弱信号,待老师追认)"

df = pd.read_excel(SRC, sheet_name="全部打分")
assert len(df) == 1368
cand = pd.read_excel(ANNO, "guide候选")
cand_by_ref = {str(r).lower(): g.sort_values("热点得分", ascending=False) for r, g in cand.groupby("ref")}
cand_by_ref.update({k[3:]: v for k, v in list(cand_by_ref.items()) if k.startswith("ref")})

def ref_of(note):
    m = re.search(r"块\d+-ref([A-Za-z0-9]+)", str(note))
    return m.group(1).lower() if m else None

def rule(top1, top2):
    if top1 < 100:
        return "D"
    if top1 >= 500 and (top2 == 0 or top1 >= 4 * top2):
        return "A"
    return "B"

pend = df.index[(df["等级"] == "待定") & (df["处理状态"] == ST_KEEP)]
assert len(pend) == 22, len(pend)
n_a = n_d = 0
for i in pend:
    ref = ref_of(df.at[i, "备注"])
    c = cand_by_ref.get(ref)
    assert c is not None, (df.at[i, "guide-id"], ref)
    top1 = float(c["热点得分"].iloc[0])
    top2 = float(c["热点得分"].iloc[1]) if len(c) > 1 else 0.0
    g = rule(top1, top2)
    if g == "A":
        assert str(df.at[i, "seq-20"]) == str(c["seq20"].iloc[0]), df.at[i, "guide-id"]
        df.at[i, "等级"] = "A"
        df.at[i, "置信分"] = 80
        df.at[i, "判定依据"] = ("QC剔除经9.19裁决撤销;reads反推唯一主导候选(Top1得分%d,次选%d),"
                          "未经设计表确认(16.1版据guide候选表补定级)" % (top1, top2))
        n_a += 1
    else:
        assert g == "D"
        df.at[i, "等级"] = "D"
        df.at[i, "置信分"] = 25
        df.at[i, "处理状态"] = ST_EXCL_WEAK
        df.at[i, "判定依据"] = ("QC剔除经9.19裁决撤销;热点得分过弱(最高仅%d),无法确定guide身份"
                          "(16.1版据guide候选表补定级;9.19裁决为保留,单列待老师追认)" % top1)
        n_d += 1
print("22 行待定补定级: A/80 ×%d (保留), D/25 ×%d (移入弱信号待追认)" % (n_a, n_d))
assert (n_a, n_d) == (16, 6)

# ---- 效率分在 969 保留行内重算 ----
keep_idx = df.index[df["处理状态"] == ST_KEEP]
N = len(keep_idx)
assert N == 969, N
assert df.loc[keep_idx, "DeepSpCas9分"].notna().all() and df.loc[keep_idx, "CRISPRon分"].notna().all()
comp = (rankdata(df.loc[keep_idx, "DeepSpCas9分"].values, "average")
        + rankdata(df.loc[keep_idx, "CRISPRon分"].values, "average")) / 2 / N * 100
df["效率综合分"] = np.nan
df["效率排名"] = np.nan
df.loc[keep_idx, "效率综合分"] = np.round(comp, 2)
df.loc[keep_idx, "效率排名"] = pd.Series(comp, index=keep_idx).rank(ascending=False, method="min")

pair = (df.loc[keep_idx, "DeepSpCas9分"].astype(str) + "|" + df.loc[keep_idx, "CRISPRon分"].astype(str))
gchk = pd.DataFrame({"pair": pair, "comp": df.loc[keep_idx, "效率综合分"], "rk": df.loc[keep_idx, "效率排名"]})
assert gchk.groupby("pair")["comp"].nunique().max() == 1 and gchk.groupby("pair")["rk"].nunique().max() == 1
ip = pd.to_numeric(df.loc[keep_idx, "indel_pct"], errors="coerce")
c = df.loc[keep_idx, "效率综合分"]
print("训练集 N=%d 分数对=%d 名次档=%d 最大并列组=%d" % (N, pair.nunique(), df.loc[keep_idx, "效率排名"].nunique(), pair.value_counts().iloc[0]))
print("r(综合分,indel_pct) pearson=%.4f spearman=%.4f" % (pearsonr(c, ip)[0], spearmanr(c, ip)[0]))
print("综合分 min=%.2f 中位=%.2f max=%.2f" % (c.min(), c.median(), c.max()))

# ---- 输出 ----
train = df[df["处理状态"] == ST_KEEP].sort_values(["效率综合分", "guide-id"], ascending=[False, True])
excl = df[df["处理状态"].isin([ST_EXCL_RULING, ST_EXCL_WEAK])].copy()
BATCH_DROP = {"USR-14333": "疑T2代测序", "USR-22807": "参照与基因型不配套"}
def reason(r):
    if r["处理状态"] == ST_EXCL_WEAK:
        return "弱信号(热点最高分<100),guide身份无法确认,待老师追认"
    if r["batch"] in BATCH_DROP:
        return "9.19裁决-整批剔除(%s%s)" % (r["batch"], BATCH_DROP[r["batch"]])
    return "9.19裁决-批注版剔除(QC口径)"
if "剔除原因细分" in excl.columns:
    excl = excl.drop(columns=["剔除原因细分"])
excl.insert(excl.columns.get_loc("处理状态") + 1, "剔除原因细分", [reason(r) for _, r in excl.iterrows()])

readme = pd.DataFrame({"16.1版说明 (2026-09-21)": [
    "16 版 + guide候选表回传后补完 22 行'待定'分级（规则与 15 版规则2/3/4 完全一致，且已对 15 版 219 行复推 100% 验证，见 scripts/dev/b_crosscheck_0921.py）。",
    "16 行 refM(Top1=68077,次选=0) → A/80 保留；6 行 refSP1(Top1=62<100) → D/25 弱信号，移入 剔除(弱信号,待老师追认)。",
    "口径算术: 1368 = 保留969(训练集sheet) + 保留-不可打分3(TKS_1131/1134/1135) + 剔除(9.19裁决)360 + 剔除(弱信号,待追认)36。",
    "训练集969 + 弱信号36 = 1005 = 9.19裁决保留的可打分行数，与 b_anchor_final_0919 锚定口径一致；老师若否决弱信号剔除，按处理状态列筛回即得 1005 行。",
    "效率综合分 = 两模型在 969 行内百分位(并列同值,average rank)→均值×100(2位小数)；效率排名 = 综合分降序 competition ranking(并列同名次)；无 tie-break 抖动（B1 修复口径同 16 版）。",
    "训练集 sheet 排序 = 综合分降序 + guide-id 升序；DeepSpCas9分/CRISPRon分 为源 CSV 全精度。",
    "等级只表征 guide 身份证据强度，剔除与否以处理状态为准；'待定'仅剩不可打分 3 行（无seq-20，待生物负责人复核）。",
    "剔除清单 sheet 396 行 = 360 裁决 + 36 弱信号，含'剔除原因细分'列；模型原始分保留，不算综合分/排名。",
    "遗留: ① 弱信号 36 行交老师追认（定 969/1005 口径）；② 双gRNA 63 行拆分待执行；③ 969/1005 口径锚定+LOGO 重跑对比。",
    "生成: scripts/dev/b_fix_161_pending_grades_0921.py；前序: b_fix_16_postruling_0921.py / b_crosscheck_0921.py；审计: results/b_audit_0920.md；说明: docs/reports/scoring_rules_16_post_ruling_0921.md",
]})

with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    df.to_excel(w, sheet_name="全部打分", index=False)
    train.to_excel(w, sheet_name="训练集", index=False)
    excl.to_excel(w, sheet_name="剔除清单", index=False)
    readme.to_excel(w, sheet_name="16.1版说明", index=False)

# ---- 终检 ----
chk = pd.read_excel(OUT, sheet_name=None)
assert len(chk["全部打分"]) == 1368 and len(chk["训练集"]) == 969 and len(chk["剔除清单"]) == 396
a = chk["全部打分"]
assert a["处理状态"].value_counts().to_dict() == {ST_KEEP: 969, ST_EXCL_RULING: 360, ST_EXCL_WEAK: 36, ST_KEEP_NS: 3}
assert (a["等级"] == "待定").sum() == 3
for gid_ in ["TKS_1141", "TKS_1170"]:
    r = a[a["guide-id"] == gid_].iloc[0]
    assert r["等级"] == "A" and r["置信分"] == 80 and r["处理状态"] == ST_KEEP, gid_
for gid_ in ["TKS_1122", "TKS_1128"]:
    r = a[a["guide-id"] == gid_].iloc[0]
    assert r["等级"] == "D" and r["处理状态"] == ST_EXCL_WEAK, gid_
t = chk["训练集"]
assert t["效率综合分"].notna().all() and t["效率综合分"].is_monotonic_decreasing
assert set(t["guide-id"]) & set(chk["剔除清单"]["guide-id"]) == set()
print("全部断言通过。已写出", OUT)
