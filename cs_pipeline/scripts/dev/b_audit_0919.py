# -*- coding: utf-8 -*-
"""b_audit_0919.py — 计B 对 problem3 报告的独立复核与敏感性实验（2026-09-19）
A. QC 剔除清单 vs 合并表备注的一致性复核（逐批对账 + 规则分布 + 差异行定位）
B. problem.md/problem2.md 已声明更正在现行数据表中的落地审计
   （6995/6999 PAM 窗口更正、4820 PAM 更正/剔除、训练表非 NGG 扫描、5712 写回核对）
C. "开关式" 100% 编辑行对纯旧数据基线 LOGO-CV 的敏感性（剔除前后对比）
输出: results/b_audit_0919.md（人读小结）+ results/b_sensitivity_logo_0919.csv
"""
import numpy as np, pandas as pd, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, LeaveOneGroupOut

out = []
def say(s=""):
    print(s); out.append(s)

say("# 计B 独立复核与敏感性实验（2026-09-19）\n")

# ============ A. QC 一致性 ============
say("## A. QC 剔除一致性复核\n")
qc = pd.read_csv("results/qc_excluded_0918.csv")
m = pd.read_csv("data/hitom/hitom_clean_merged_0918.csv")
m["note"] = m["note"].fillna("")
m_qc = m[m["note"].str.contains("QC剔除")]
say(f"- qc_excluded_0918.csv: {len(qc)} 行 / {qc['batch'].nunique()} 批次")
say(f"- hitom_clean_merged_0918.csv 备注含 QC剔除: {len(m_qc)} 行 / 全表 {len(m)} 行")
# 规则分布
rules = qc["备注"].str.extract(r"QC剔除\(([^)]+)\)")[0].str.replace(r"\d+%", "N%", regex=True)
say("\n剔除规则分布（按 qc 清单备注）:")
say(rules.value_counts().to_string())
# 逐批对账（报告 4.① 声称: 6883 82/94, 6137 55/80, 6444 33/48, 7342 19/26）
claim = {"USR-6883": (82, 94), "USR-6137": (55, 80), "USR-6444": (33, 48), "USR-7342": (19, 26)}
say("\n逐批剔除数对账（清单 vs 报告声称）:")
per = qc.groupby("batch").size()
for b, (ex, tot) in claim.items():
    say(f"- {b}: 清单 {per.get(b, 0)} / 报告 {ex}（总 {tot}）  {'✅一致' if per.get(b,0)==ex else '❌不一致'}")
# 350 vs 347 差异定位：按 guide-id 比对
# merged 表的 guide_id 与 qc 清单的 guide-id 是否同一命名
qids = set(qc["guide-id"].astype(str))
mids = set(m_qc["guide_id"].astype(str))
say(f"\n编号交集: qc清单 {len(qids)} 唯一ID,  merged QC行 {len(mids)} 唯一ID,  交集 {len(qids & mids)}")
only_qc = sorted(qids - mids); only_m = sorted(mids - qids)
if only_qc: say(f"- 仅在清单: {only_qc[:10]}")
if only_m: say(f"- 仅在 merged: {only_m[:10]}")
# 备注规则文本两边是否一致（对交集行）
mm = m_qc.set_index("guide_id")
both = qids & mids
mism = 0
for gid in both:
    r1 = qc.loc[qc["guide-id"].astype(str) == gid, "备注"].iloc[0]
    r2 = mm.loc[gid, "note"]
    g1 = re.search(r"QC剔除\(([^)]+)\)", str(r1)); g2 = re.search(r"QC剔除\(([^)]+)\)", str(r2))
    if (g1 and g2) and g1.group(1)[:4] != g2.group(1)[:4]:
        mism += 1
say(f"- 交集行剔除原因文本不一致数: {mism}")

# ============ B. 更正落地审计（487 行基线表） ============
say("\n## B. 已声明更正在现行基线表中的落地审计\n")
f = pd.read_csv("data/hitom/hitom_seq30_full_0916.csv")
say(f"基线表 hitom_seq30_full_0916.csv: {len(f)} 行")
# B1. 6995/6999 窗口更正
g69 = f[f["gene_id"].str.contains("6995|6999", na=False)]
say(f"\nB1. LG01.6995/6999 行数: {len(g69)}")
if len(g69):
    say(f"    seq20 唯一值: {sorted(g69['seq20'].unique())}")
    say(f"    pam 唯一值: {sorted(g69['pam'].unique())}")
    exp = "CGTAAGGATTGCTGCTGAGA"
    ok_seq = (g69["seq20"] == exp).all()
    ok_pam = (g69["pam"] == "AGG").all()
    say(f"    更正后期望 seq20={exp}, pam=AGG → seq {'✅' if ok_seq else '❌'}, pam {'✅' if ok_pam else '❌'}")
    for gene, exp_se in [("6995", (165462914, 165462934)), ("6999", (165502832, 165502852))]:
        sub = g69[g69["gene_id"].str.contains(gene)]
        if len(sub):
            ok = ((sub["start"] == exp_se[0]) & (sub["end"] == exp_se[1])).all()
            say(f"    {gene}: {len(sub)} 行, 坐标 {sub['start'].iloc[0]}-{sub['end'].iloc[0]}, 期望 {exp_se[0]}-{exp_se[1]} {'✅' if ok else '❌'}")
# B2. LG02.4820 四行 PAM
g48 = f[f["gene_id"].str.contains("4820", na=False)]
say(f"\nB2. LG02.4820 行数: {len(g48)}")
if len(g48):
    say(g48.groupby(["seq20", "pam"]).size().to_string())
    bad = g48[g48["seq20"] == "AACATGGTTCGAGTTCAAGA"]
    say(f"    问题 guide AACATGGTTCGAGTTCAAGA 在基线表中: {len(bad)} 行", )
    if len(bad): say(f"    其 pam 值: {sorted(bad['pam'].unique())}（problem.md 记录原值 CCA，9.16 更正为 ACT 且 00 脚本应剔除非 NGG）")
# B3. 全表非 NGG PAM 扫描
ngg = f["pam"].astype(str).str.match(r"^[ACGT]GG$")
say(f"\nB3. 基线表非 NGG PAM 行数: {(~ngg).sum()}")
if (~ngg).sum():
    say(f.loc[~ngg, ["uid", "gene_id", "seq20", "pam"]].to_string(index=False))
# B4. 5712 写回核对
r5712 = f[f["batch"] == "USR-5712"]
say(f"\nB4. USR-5712 批行数: {len(r5712)}, indel_pct 中位数: {r5712['indel_pct'].median():.4f}（problem2 称写回后中位数 1.0）")
try:
    wb = pd.read_csv("data/hitom/usr5712_indel_rightside_recompute_0915.csv")
    say(f"    重算表列: {list(wb.columns)}")
except Exception as e:
    say(f"    重算表读取失败: {e}")

# ============ C. 开关式 100% 行敏感性 ============
say("\n## C. 100% 编辑行对基线 LOGO-CV 的敏感性\n")
df = f.copy()
deep = pd.read_csv("results/scores_deepspcas9_full_0916.csv")
crisp = pd.read_csv("results/scores_crispron_full_0916.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
sw = df[np.isclose(df["indel_pct"].round(6), 1.0)]
say(f"- indel_pct=1.0（round6）行数: {len(sw)} / {len(df)}")
say("- 按基因分布:")
say(sw.groupby("gene_id").size().to_string())
say("- 按批次分布:")
say(sw.groupby("batch").size().to_string())

df["gc_total"] = df.seq20.map(gc_fraction)
df["gc_seed"] = df.seq30.str[18:24].map(gc_fraction)
df["tm"] = df.seq20.map(Tm_NN)
df["poly_t"] = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_")) or c in ("tm", "poly_t")]
HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999", "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)
assert not df[FEATS].isna().any().any()

def logo(d, name):
    X = d[FEATS].astype(float).values
    y = d["efficiency_norm"].astype(float).values
    g = d["gene_group"].values
    rhos = []
    for tr_i, te_i in LeaveOneGroupOut().split(X, y, g):
        cv_i = list(GroupKFold(min(5, len(set(g[tr_i])))).split(X[tr_i], y[tr_i], g[tr_i]))
        gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)}, cv=cv_i, scoring="neg_mean_squared_error")
        gs.fit(X[tr_i], y[tr_i])
        p = gs.best_estimator_.predict(X[te_i])
        if len(set(np.round(y[te_i], 6))) > 1 and len(set(np.round(p, 6))) > 1:
            rhos.append(spearmanr(p, y[te_i])[0])
    med = float(np.nanmedian(rhos))
    say(f"- [{name}] n={len(d)}, 基因分组={len(set(g))}, 有效折={len(rhos)}, LOGO-CV 中位 rho = {med:.4f}")
    return {"variant": name, "n_rows": len(d), "n_groups": len(set(g)), "n_folds": len(rhos), "logo_cv_median_rho": round(med, 4)}

res = [logo(df, "baseline_all487")]
res.append(logo(df[~np.isclose(df["indel_pct"].round(6), 1.0)], "drop_indel_eq_1"))
# 附加: 剔除整个 USR-8145 批（100% 行最集中）对照
res.append(logo(df[df["batch"] != "USR-8145"], "drop_USR8145"))
pd.DataFrame(res).to_csv("results/b_sensitivity_logo_0919.csv", index=False)
say("\nSaved results/b_sensitivity_logo_0919.csv")

with open("results/b_audit_0919.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("\nSaved results/b_audit_0919.md")
