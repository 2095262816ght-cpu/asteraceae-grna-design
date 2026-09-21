# -*- coding: utf-8 -*-
"""b_fix_16_postruling_0921.py — 15版审计整改（b_audit_0920.md B1/B2），产出 16 版

B2 修复：以 results/excluded_gids_final_0919.csv（360 gid，老师批注版最终裁决）为唯一裁决源重算处理状态
  - 15版误保留 28 行（USR-14333×25 / USR-22807×3，9.19 裁决整批剔除）→ 剔除(9.19裁决)
  - 15版误剔 64 行 QC撤销行（USR-5448×12 / USR-6137×52）→ 恢复保留，并按15版规则重定级
  - TKS_1131/1134/1135：QC撤销但无 seq-20/无模型分 → 保留(不可打分,待复核)，不进训练集
  - 弱信号 30 行（热点<100，guide 身份无法确认；9.19 裁决为保留）→ 单列 剔除(弱信号,待老师追认)
  - 裁决回写备注列（USR-14333/22807 全批、QC撤销行），防止后续再次脱节
B1 修复：效率综合分 = 两模型组内百分位(并列同值, average rank) → 均值×100（2位小数），无 tie-break 抖动；
  效率排名 = 综合分降序 competition ranking（并列同名次, method='min'）；
  训练集 sheet 排序 = 综合分降序 + guide-id 升序（确定性）
口径算术：1368 = 保留975 + 保留-不可打分3 + 剔除(9.19裁决)360 + 剔除(弱信号,待追认)30
输出：data/1_Hi-results-16-efficiency-20260921.xlsx（全部打分/训练集/剔除清单/16版说明）
运行：cd cs_pipeline && python scripts/dev/b_fix_16_postruling_0921.py
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata, pearsonr, spearmanr

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "data/1_Hi-results-15-efficiency-20260920.xlsx"
EXCL_CSV = "results/excluded_gids_final_0919.csv"
DEEP = "results/scores_deepspcas9_merged_0918.csv"
CRIS = "results/scores_crispron_merged_0918.csv"
OUT = "data/1_Hi-results-16-efficiency-20260921.xlsx"

ST_KEEP = "保留"
ST_KEEP_NS = "保留(不可打分,待复核)"
ST_EXCL_RULING = "剔除(9.19裁决)"
ST_EXCL_WEAK = "剔除(弱信号,待老师追认)"
BATCH_DROP = {"USR-14333": "疑T2代测序", "USR-22807": "参照与基因型不配套"}
UNSCOREABLE = {"TKS_1131", "TKS_1134", "TKS_1135"}

df = pd.read_excel(SRC, sheet_name="全部打分")
assert len(df) == 1368, len(df)
BASE14 = list(df.columns[:14])
orig_note = df["备注"].fillna("").astype(str).copy()
orig_basis = df["判定依据"].fillna("").astype(str).copy()

excl = set(pd.read_csv(EXCL_CSV)["guide-id"].astype(str))
assert len(excl) == 360, len(excl)
gid = df["guide-id"].astype(str)
deep = dict(zip(pd.read_csv(DEEP)["guide_id"].astype(str), pd.read_csv(DEEP)["deepspcas9_score"]))
cris = dict(zip(pd.read_csv(CRIS)["guide_id"].astype(str), pd.read_csv(CRIS)["crispron_score"]))

in_excl = gid.isin(excl)
weak15 = orig_basis.str.contains("热点得分过弱")
excl15 = df["处理状态"] == "剔除"

m_ruling = in_excl                                    # 360
m_weak30 = weak15 & ~in_excl                          # 30
m_nscore = ~in_excl & ~weak15 & gid.isin(UNSCOREABLE)  # 3
m_revoked = ~in_excl & ~weak15 & excl15 & ~m_nscore   # 64 (QC撤销恢复)
m_keep = ~in_excl & ~weak15 & ~m_nscore & ~m_revoked  # 911 (15版保留且裁决保留)
print("分类行数: 裁决剔除=%d 弱信号待追认=%d 不可打分=%d QC撤销恢复=%d 原样保留=%d 合计=%d"
      % (m_ruling.sum(), m_weak30.sum(), m_nscore.sum(), m_revoked.sum(), m_keep.sum(),
         m_ruling.sum() + m_weak30.sum() + m_nscore.sum() + m_revoked.sum() + m_keep.sum()))
assert m_ruling.sum() == 360 and m_weak30.sum() == 30 and m_nscore.sum() == 3
assert m_revoked.sum() == 64 and m_keep.sum() == 911
assert (m_ruling | m_weak30 | m_nscore | m_revoked | m_keep).all()
assert sum(x.sum() for x in (m_ruling & m_weak30, m_ruling & m_revoked, m_keep & m_revoked)) == 0

# ---- 处理状态 / 9.19裁决 列 ----
status = pd.Series("", index=df.index)
status[m_ruling] = ST_EXCL_RULING
status[m_weak30] = ST_EXCL_WEAK
status[m_nscore] = ST_KEEP_NS
status[m_revoked | m_keep] = ST_KEEP
ruling = pd.Series(np.where(in_excl, "剔除", "保留"), index=df.index)

# ---- 等级/置信分/判定依据 修正 ----
grade = df["等级"].astype(str).copy()
conf = pd.to_numeric(df["置信分"], errors="coerce").astype(float).copy()
basis = orig_basis.copy()

note = orig_note.copy()
note[df["batch"].isin(BATCH_DROP)] = [
    (n + "; 9.19老师裁决:整批剔除(%s)" % BATCH_DROP[b]) if n else ("9.19老师裁决:整批剔除(%s)" % BATCH_DROP[b])
    for n, b in zip(note[df["batch"].isin(BATCH_DROP)], df.loc[df["batch"].isin(BATCH_DROP), "batch"])
]
revoked_note = note[m_revoked]
note[m_revoked] = revoked_note + "; 9.19老师裁决:QC撤销(5448杂合子材料/6137批次保留)"
note[m_nscore] = note[m_nscore] + "; 9.19老师裁决:QC撤销(待生物负责人复核)"

# 28 行误保留 → 裁决剔除（等级保留原证据分级，判定依据加注）
m28 = m_ruling & (df["处理状态"] == "保留")
print("15版误保留、本次按裁决剔除: %d 行 (批次: %s)" % (m28.sum(), df.loc[m28, "batch"].value_counts().to_dict()))
assert m28.sum() == 28
basis[m28] = basis[m28] + "; 16版更正:9.19裁决整批剔除,15版误保留"

# 30 行弱信号（裁决保留但身份无法确认）
basis[m_weak30] = basis[m_weak30] + "; 16版:9.19裁决为保留,因guide身份无法确认单列待老师追认"

# 64 行 QC撤销恢复 → 按15版规则重定级
def regrade(row_note: str):
    if "guide确定" in row_note:
        return "A", 88, "QC剔除经9.19裁决撤销;计B经reads/Sheet2核实确认guide身份"
    if "更正" in row_note:
        return "A", 85, "QC剔除经9.19裁决撤销;原记录有误,已经原始reads+基因组核实更正"
    if ("待设计表确认" in row_note) or ("guide未确定" in row_note):
        return "待定", np.nan, "QC剔除经9.19裁决撤销;guide身份分级需guide候选表热点得分,表未回传,暂记待定"
    return "A", 90, "QC剔除经9.19裁决撤销;原主表登记行,无争议"

rg = [regrade(n) for n in orig_note[m_revoked]]
grade[m_revoked] = [x[0] for x in rg]
conf[m_revoked] = [x[1] for x in rg]
basis[m_revoked] = [x[2] for x in rg]
print("QC撤销 64 行重定级:", pd.Series([x[0] for x in rg]).value_counts().to_dict())

grade[m_nscore] = "待定"
conf[m_nscore] = np.nan
basis[m_nscore] = "QC剔除经9.19裁决撤销;无seq-20(测序编辑率≈0无突变热点),不可打分,待生物负责人复核"

# ---- 模型分（全精度）与效率综合分/排名（仅 975 保留行）----
df["DeepSpCas9分"] = gid.map(deep)
df["CRISPRon分"] = gid.map(cris)
tr_idx = df.index[m_keep | m_revoked]
tr = df.loc[tr_idx]
assert tr["DeepSpCas9分"].notna().all() and tr["CRISPRon分"].notna().all()
N = len(tr)
comp = (rankdata(tr["DeepSpCas9分"].values, "average")
        + rankdata(tr["CRISPRon分"].values, "average")) / 2 / N * 100
df["效率综合分"] = np.nan
df.loc[tr_idx, "效率综合分"] = np.round(comp, 2)
df["效率排名"] = np.nan
df.loc[tr_idx, "效率排名"] = pd.Series(comp, index=tr_idx).rank(ascending=False, method="min").astype(float)

# 并列校验：分数对相同 → 综合分/排名必须相同
pair = tr["DeepSpCas9分"].astype(str) + "|" + tr["CRISPRon分"].astype(str)
g = pd.DataFrame({"pair": pair, "comp": df.loc[tr_idx, "效率综合分"], "rk": df.loc[tr_idx, "效率排名"]})
assert g.groupby("pair")["comp"].nunique().max() == 1, "同分数对综合分不一致"
assert g.groupby("pair")["rk"].nunique().max() == 1, "同分数对排名不一致"
n_pairs = g["pair"].nunique()
comp_unrounded = comp
print("训练集 N=%d, 不同分数对=%d, 不同综合分(未舍入)=%d, 不同综合分=%d, 不同名次=%d (并列同名次)"
      % (N, n_pairs, len(np.unique(np.round(comp_unrounded, 6))),
         df.loc[tr_idx, "效率综合分"].nunique(), int(df.loc[tr_idx, "效率排名"].nunique())))
assert int(df.loc[tr_idx, "效率排名"].nunique()) == df.loc[tr_idx, "效率综合分"].nunique()
assert int(df.loc[tr_idx, "效率综合分"].nunique()) <= n_pairs

ip = pd.to_numeric(tr["indel_pct"], errors="coerce")
c = df.loc[tr_idx, "效率综合分"]
print("r(综合分,indel_pct) pearson=%.4f spearman=%.4f (n=%d)"
      % (pearsonr(c, ip)[0], spearmanr(c, ip)[0], N))
print("综合分 min=%.2f 中位=%.2f mean=%.2f max=%.2f; 最大并列组=%d 行"
      % (c.min(), c.median(), c.mean(), c.max(), pair.value_counts().iloc[0]))

# ---- 组装输出 ----
out = df[BASE14].copy()
out["备注"] = note
out["等级"] = grade
out["置信分"] = conf
out["9.19裁决"] = ruling
out["处理状态"] = status
out["判定依据"] = basis
for col in ["DeepSpCas9分", "CRISPRon分", "效率综合分", "效率排名"]:
    out[col] = df[col]

# base 其余 13 列与 15 版逐格一致校验
src14 = pd.read_excel(SRC, sheet_name="全部打分")[BASE14]
for col in BASE14:
    if col == "备注":
        assert (out[col].fillna("") == note).all()
        changed = (out[col].fillna("") != src14[col].fillna("")).sum()
        print("备注列追加裁决回写: %d 行 (USR-14333/22807 全批 + QC撤销 67 行)" % changed)
    else:
        assert (out[col].astype(str) == src14[col].astype(str)).all(), col

train = out[out["处理状态"] == ST_KEEP].sort_values(["效率综合分", "guide-id"], ascending=[False, True])
excl_sheet = out[out["处理状态"].isin([ST_EXCL_RULING, ST_EXCL_WEAK])].copy()
def reason(r):
    if r["处理状态"] == ST_EXCL_WEAK:
        return "弱信号(热点最高分<100),guide身份无法确认,待老师追认"
    if r["batch"] in BATCH_DROP:
        return "9.19裁决-整批剔除(%s%s)" % (r["batch"], BATCH_DROP[r["batch"]])
    return "9.19裁决-批注版剔除(QC口径)"
excl_sheet.insert(excl_sheet.columns.get_loc("处理状态") + 1, "剔除原因细分",
                  [reason(r) for _, r in excl_sheet.iterrows()])

readme = pd.DataFrame({"16版说明 (2026-09-21)": [
    "依据 results/b_audit_0920.md 对 15 版的 B1/B2 两个阻断问题的修正版；基线=15版全部打分 sheet。",
    "base 14 列与 13-merged 逐格一致，唯一改动是备注列追加 9.19 裁决回写（防再次脱节）。",
    "口径算术: 1368 = 保留975(训练集sheet) + 保留-不可打分3 + 剔除(9.19裁决)360 + 剔除(弱信号,待追认)30。",
    "处理状态定义:",
    "  保留 — 9.19裁决保留且guide身份可定、有模型分 → 进训练集 sheet（975 行）。",
    "  保留(不可打分,待复核) — TKS_1131/1134/1135: 9.19 QC撤销保留，但无seq-20/无模型分，待生物负责人复核，不进训练集。",
    "  剔除(9.19裁决) — excluded_gids_final_0919.csv 全部 360 行（QC口径 + USR-14333/USR-22807 整批剔除），含 15 版误保留的 28 行。",
    "  剔除(弱信号,待老师追认) — 热点最高分<100、guide身份无法确认的 30 行；9.19裁决为保留，16版单列不进训练集；老师追认恢复后训练集=1005 行裁决口径。",
    "等级/置信分 — 沿用 15 版 guide 身份证据分级；64 行 QC撤销行按 15 版规则重定级（guide确定→A/88、更正→A/85、无批注→A/90）；",
    "  需要 guide候选表热点得分才能分级的行标'待定'（guide候选表在同学处，回传后补齐）。等级只表征证据强度，剔除与否以处理状态为准。",
    "效率综合分 — 两模型在 975 行内的百分位（并列同值，average rank）→ 均值×100，2位小数；无 15 版的 0.1 tie-break 抖动（B1 修复）。",
    "效率排名 — 综合分降序 competition ranking（并列同名次，method='min'）；975 行只有 38 个不同分数对 → 38 个名次档位。",
    "训练集 sheet 排序 — 综合分降序 + guide-id 升序（确定性排序）。",
    "剔除清单 sheet — 390 行 = 360 裁决 + 30 弱信号，新增'剔除原因细分'列；模型原始分保留，不算综合分/排名。",
    "遗留: ① guide候选表(61条)回传后补'待定'行分级；② 弱信号规则是否成立交老师追认；③ 双gRNA 63 行 -A/-B 拆分待执行（沿用15版标记）。",
    "生成脚本: scripts/dev/b_fix_16_postruling_0921.py（可复现）；审计: results/b_audit_0920.md；说明: docs/reports/scoring_rules_16_post_ruling_0921.md",
]})

with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    out.to_excel(w, sheet_name="全部打分", index=False)
    train.to_excel(w, sheet_name="训练集", index=False)
    excl_sheet.to_excel(w, sheet_name="剔除清单", index=False)
    readme.to_excel(w, sheet_name="16版说明", index=False)

# ---- 终检 ----
chk = pd.read_excel(OUT, sheet_name=None)
assert len(chk["全部打分"]) == 1368 and len(chk["训练集"]) == 975 and len(chk["剔除清单"]) == 390
t = chk["训练集"]
assert t["效率综合分"].notna().all() and t["效率排名"].notna().all()
assert t["效率综合分"].is_monotonic_decreasing
allc = chk["全部打分"]
for g_ in ["TKS_0493", "TKS_0575", "TKS_0661", "TKS_0668"]:
    assert allc.loc[allc["guide-id"] == g_, "处理状态"].iloc[0] == ST_EXCL_RULING, g_
for g_ in ["TKS_1084", "TKS_1113"]:
    assert allc.loc[allc["guide-id"] == g_, "处理状态"].iloc[0] == ST_KEEP, g_
for g_ in UNSCOREABLE:
    assert allc.loc[allc["guide-id"] == g_, "处理状态"].iloc[0] == ST_KEEP_NS, g_
assert set(chk["剔除清单"]["guide-id"]) & set(t["guide-id"]) == set()
print("全部断言通过。已写出", OUT)
