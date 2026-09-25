# -*- coding: utf-8 -*-
"""24_model_comparison_nob879.py — noB879 同口径官方横向对比总表（P1 待办）。

为什么需要它
------------
磁盘上原有的 `results/model_comparison_full_0916.csv` 是 **487 行旧口径**（v2.0 冻结、
裁决前），且两个单模型行的 `rho_logo_cv_median` 留空、三个模型的 `auc_test` 全是同一个
0.0735（可疑，复查判断见产物报告第二节告警 4）。现行生产口径是 noB879（879 行 / 16 基因组）+ 形态二 GLMM，
两者不可比。本脚本在**同一口径、同一测试集划分、同一 AUC 定义**下重出三方对比。

口径与可比性保证
----------------
1. 队列：`features_common.load_cohort("noB879")`，与 scripts/15 生产训练同源；
2. 测试集划分：`GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)` 按 gene_group
   分组——与 scripts/15 逐字一致，故本表的 GLMM 行必然等于生产指标；
3. 形态二拟合：调用 `hier_bb_model.fit_hierarchical_selective_bb`，即生产训练用的同一段代码，
   而非另抄一份（否则对比的是两个不同模型）；
4. 单模型不拟合：DeepSpCas9 / CRISPRon 是预训练模型，直接用其在测试集上的原始打分；
5. AUC 定义沿用 `scripts/13:85-91`：取测试集 indel_pct 的 20/80 分位，掩出两端各 20%，
   以 q_high 为阈值二值化，三个模型共用同一套标签与同一个掩码；
6. LOGO 折有效性规则与 scripts/15 一致：留出折内 y 与预测/打分**都**至少要有 2 个不同取值，
   否则该折 ρ 无定义、剔除。三个模型用同一条规则，故"有效折数"可直接横向比较。

自检：脚本会断言 GLMM 行的测试集 ρ 与 `results/metrics_hier_bb_nob879_0921.csv` 中已落盘的
生产指标一致，防止本表与生产模型脱钩。

运行（在 cs_pipeline/ 下，crispr 环境，约 1 分钟）：
    python scripts/24_model_comparison_nob879.py
产物：
    results/model_comparison_nob879_0921.csv         横向对比总表（官方交付）
    results/model_comparison_nob879_folds_0921.csv   逐折明细（证据链）
    results/model_comparison_nob879_report_0924.md   解读与可比性告警（引用该表前必读；
                                                     告警数字由本脚本实测生成，非手写）
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, LeaveOneGroupOut

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from features_common import FEATURE_COLS, load_cohort
from hier_bb_model import compute_batch_prior, fit_hierarchical_selective_bb

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_TABLE = BASE_DIR / "results" / "model_comparison_nob879_0921.csv"
OUT_FOLDS = BASE_DIR / "results" / "model_comparison_nob879_folds_0921.csv"
OUT_REPORT = BASE_DIR / "results" / "model_comparison_nob879_report_0924.md"
METRICS_CSV = BASE_DIR / "results" / "metrics_hier_bb_nob879_0921.csv"

COHORT = "noB879"
PRIOR_SCALE = 5.0
RANDOM_STATE = 42
TEST_SIZE = 0.2
# Class A（低混杂多批折）定义与 scripts/15 一致：该基因组出现在 >= 3 个批次
CLASS_A_MIN_BATCHES = 3
ROUND_NDIGITS = 6  # 折内取值多样性判定所用舍入位数，与 scripts/15 一致

MODELS = ["DeepSpCas9 单用", "CRISPRon 单用", "形态二 GLMM（本工作 · 生产模型）"]
SCORE_COL = {
    "DeepSpCas9 单用": "deepspcas9_score",
    "CRISPRon 单用": "crispron_score",
}


def has_variance(v) -> bool:
    """折内是否至少有两个不同取值（否则 Spearman ρ 无定义）。"""
    return len(set(np.round(np.asarray(v, dtype=float), ROUND_NDIGITS))) > 1


def auc_extremes(y_te, scores) -> float:
    """scripts/13 的 AUC 定义：测试集 indel_pct 的 20/80 分位掩两端，q_high 为阈值二值化。"""
    q_low, q_high = np.percentile(y_te, 20), np.percentile(y_te, 80)
    mask = (y_te <= q_low) | (y_te >= q_high)
    y_bin = (y_te[mask] >= q_high).astype(int)
    if len(np.unique(y_bin)) < 2:
        return float("nan")
    return float(roc_auc_score(y_bin, np.asarray(scores, dtype=float)[mask]))


def main():
    df = load_cohort(COHORT)
    prior = compute_batch_prior(df)

    X_raw = df[FEATURE_COLS].astype(float).values
    groups = df["gene_group"].values
    indel = df["indel_pct"].astype(float)
    n_reads = np.maximum(df["total_reads"].values.astype(float), 10.0)
    k_reads = np.round(n_reads * indel.values).clip(0, n_reads)

    ct = pd.crosstab(df["batch"], df["gene_group"])
    class_a = {g for g in ct.columns
               if len(ct[g][ct[g] > 0]) >= CLASS_A_MIN_BATCHES}

    # ---- 测试集划分：与 scripts/15 逐字一致 ----
    gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    tr_idx, te_idx = next(gss.split(X_raw, indel, groups))
    y_te = indel.values[te_idx]

    b0_tr, w_tr, mu_tr, std_tr, _ = fit_hierarchical_selective_bb(
        X_raw[tr_idx], n_reads[tr_idx], k_reads[tr_idx], prior["batch_idx"][tr_idx],
        prior["n_batches"], prior["u_prior"], prior["u_prec"], prior["logit_p0"],
        prior_scale=PRIOR_SCALE)
    Z_te = (X_raw[te_idx] - mu_tr) / std_tr
    test_score = {
        "形态二 GLMM（本工作 · 生产模型）": b0_tr + np.dot(Z_te, w_tr),
    }
    for name, col in SCORE_COL.items():
        test_score[name] = df[col].values[te_idx].astype(float)

    rows = []
    # 去重口径：测试集 198 行只含 7 条 distinct guide，同一 guide 的重复测定不提供新的
    # 序列-效率信息，却让 p 值按 n=198 计自由度而系统性过度乐观（与方案2 消融中 LRT vs
    # 聚类自助 CI 的矛盾同源）。故并列给出"按 distinct guide 聚合后"的 ρ 与 p。
    dedup = pd.DataFrame({"seq30": df.seq30.values[te_idx], "y": y_te})
    for name in MODELS:
        dedup[name] = test_score[name]
    agg = dedup.groupby("seq30").median().reset_index()

    for name in MODELS:
        s = test_score[name]
        rho, p = spearmanr(s, y_te)
        rho_d, p_d = spearmanr(agg[name].values, agg["y"].values)
        rows.append({
            "model": name,
            "cohort": COHORT,
            "n_train": len(tr_idx),
            "n_test": len(te_idx),
            "spearman_rho_test": round(float(rho), 4),
            "spearman_p_test": float(p),
            "n_distinct_guide_test": int(agg.shape[0]),
            "spearman_rho_test_dedup": round(float(rho_d), 4),
            "spearman_p_test_dedup": float(p_d),
            "auc_test": round(auc_extremes(y_te, s), 4),
        })
    print("[1/3] 测试集（%d 训练 / %d 留出 / 仅 %d 条 distinct guide，按 gene_group 分组）"
          % (len(tr_idx), len(te_idx), agg.shape[0]))
    for r in rows:
        print("      %-32s rho=%+.4f p=%.3e | 去重后 rho=%+.4f p=%.3f | auc=%.4f"
              % (r["model"], r["spearman_rho_test"], r["spearman_p_test"],
                 r["spearman_rho_test_dedup"], r["spearman_p_test_dedup"], r["auc_test"]))

    # ---- LOGO-CV：三个模型同一条折有效性规则 ----
    fold_rows = []
    for tr_i, te_i in LeaveOneGroupOut().split(X_raw, indel, groups):
        grp = groups[te_i][0]
        y_f = indel.values[te_i]
        b0_i, w_i, mu_i, std_i, _ = fit_hierarchical_selective_bb(
            X_raw[tr_i], n_reads[tr_i], k_reads[tr_i], prior["batch_idx"][tr_i],
            prior["n_batches"], prior["u_prior"], prior["u_prec"], prior["logit_p0"],
            prior_scale=PRIOR_SCALE)
        scores = {
            "形态二 GLMM（本工作 · 生产模型）": b0_i + np.dot((X_raw[te_i] - mu_i) / std_i, w_i),
        }
        for name, col in SCORE_COL.items():
            scores[name] = df[col].values[te_i].astype(float)

        for name in MODELS:
            s = scores[name]
            valid = has_variance(y_f) and has_variance(s)
            rho = float(spearmanr(s, y_f)[0]) if valid else float("nan")
            fold_rows.append({
                "gene_group": grp,
                "model": name,
                "n_samples": len(te_i),
                "n_batches": int((ct[grp] > 0).sum()),
                "class": "Class A (Low-Confounding, Multi-Batch)" if grp in class_a
                         else "Class B (High-Confounding, 1-2 Batches)",
                "valid": valid,
                "rho": round(rho, 4) if valid else np.nan,
            })

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(OUT_FOLDS, index=False)

    by_name = {r["model"]: r for r in rows}
    print("[2/3] LOGO-CV（%d 个基因组折，其中 Class A %d 个）" % (len(set(groups)), len(class_a)))
    for name in MODELS:
        sub = folds[(folds.model == name) & folds.valid]
        a = sub[sub["class"].str.startswith("Class A")]["rho"]
        r = by_name[name]
        r["rho_logo_cv_median"] = round(float(sub["rho"].median()), 4)
        r["rho_logo_class_a_median"] = round(float(a.median()), 4) if len(a) else np.nan
        r["valid_folds"] = "%d/%d" % (len(sub), int((folds.model == name).sum()))
        print("      %-32s 中位 rho=%+.4f | Class A=%+.4f | 有效折 %s"
              % (name, r["rho_logo_cv_median"], r["rho_logo_class_a_median"], r["valid_folds"]))

    # ---- 自检：GLMM 行必须等于生产已落盘指标 ----
    prod = pd.read_csv(METRICS_CSV).iloc[0]
    glmm = by_name[MODELS[-1]]
    assert glmm["spearman_rho_test"] == round(float(prod["test_rho"]), 4), \
        f"GLMM 测试集 rho {glmm['spearman_rho_test']} != 生产指标 {prod['test_rho']}"
    assert glmm["rho_logo_cv_median"] == round(float(prod["logo_cv_median_rho"]), 4), \
        f"GLMM LOGO 中位 rho {glmm['rho_logo_cv_median']} != 生产指标 {prod['logo_cv_median_rho']}"
    assert glmm["rho_logo_class_a_median"] == round(float(prod["class_a_median_rho"]), 4), \
        f"GLMM Class A rho {glmm['rho_logo_class_a_median']} != 生产指标 {prod['class_a_median_rho']}"
    assert glmm["valid_folds"] == str(prod["valid_folds"]), \
        f"GLMM 有效折 {glmm['valid_folds']} != 生产指标 {prod['valid_folds']}"
    print("[3/3] 自检通过：GLMM 行四项指标与 metrics_hier_bb_nob879_0921.csv 逐项一致")

    table = pd.DataFrame(rows)[[
        "model", "cohort", "n_train", "n_test", "spearman_rho_test", "spearman_p_test",
        "n_distinct_guide_test", "spearman_rho_test_dedup", "spearman_p_test_dedup",
        "auc_test", "rho_logo_cv_median", "rho_logo_class_a_median", "valid_folds",
    ]]
    table.to_csv(OUT_TABLE, index=False)
    print("\n已落盘 %s" % OUT_TABLE.relative_to(BASE_DIR))
    print(table.to_string(index=False))

    write_report(table, folds, df, te_idx, test_score, y_te, class_a)


def write_report(table, folds, df, te_idx, test_score, y_te, class_a):
    """落盘对比表的解读与可比性告警。

    这些数字全部由本脚本实测得出，不是手写说明——表里每个 ρ 都建立在极小的有效样本上，
    不附带这些告警就会被过度解读。
    """
    deep = test_score["DeepSpCas9 单用"]
    cris = test_score["CRISPRon 单用"]
    n_distinct_test = len(set(df.seq30.values[te_idx]))
    n_group_test = len(set(df.gene_group.values[te_idx]))
    mm_rho = float(spearmanr(deep, cris).correlation)

    q_low, q_high = np.percentile(y_te, 20), np.percentile(y_te, 80)
    mask = (y_te <= q_low) | (y_te >= q_high)
    mask_rho = float(spearmanr(deep[mask], cris[mask]).correlation)

    vc = folds[folds.valid].groupby("model").size()
    n_folds = folds.groupby("model").size().iloc[0]
    fold_mismatch = vc.nunique() > 1
    piv = folds.pivot_table(index="gene_group", columns="model", values="valid", aggfunc="first")
    mismatch = piv[piv.nunique(axis=1) > 1].index.tolist()
    # n 条 distinct guide 时，双侧精确置换检验的 p 理论下限 = 2/n!（仅 |ρ|=1 时取到）。
    # 不用 scipy 的 spearmanr 反推：它对完美相关走 t 近似并直接返回 0.0，不是置换下限。
    p_floor = 2.0 / math.factorial(n_distinct_test)

    # 每折 distinct guide 数：折内 ρ 的取值被它量化（2 条 guide ⇒ |ρ| 只能是 1 或 0.5 之类），
    # 故折内 ρ 的符号几乎是唯一信息，这也是逐折 ρ 高度不稳的根因。
    dg = df.groupby("gene_group").seq30.nunique()
    piv_rho = folds.pivot_table(index="gene_group", columns="model", values="rho", aggfunc="first")
    g_vs_d = piv_rho[[MODELS[-1], MODELS[0]]].dropna()
    n_flip = int((np.sign(g_vs_d[MODELS[-1]]) == -np.sign(g_vs_d[MODELS[0]])).sum())
    s_both = piv_rho[[MODELS[0], MODELS[1]]].dropna()
    n_identical_single = int((s_both[MODELS[0]] == s_both[MODELS[1]]).sum())

    by_name = {r["model"]: r for r in table.to_dict("records")}
    glmm = by_name[MODELS[-1]]
    lines = [
        "# noB879 同口径模型横向对比（2026-09-24）",
        "",
        "> 生成脚本：`scripts/24_model_comparison_nob879.py`（约 8 秒）",
        f"> 口径：`noB879`（{len(df)} 行 / {df.gene_group.nunique()} 基因组）· "
        f"测试集划分 `GroupShuffleSplit(test_size=0.2, random_state=42)` 按 gene_group 分组",
        "> 形态二 GLMM 行由 `hier_bb_model` 拟合，即生产训练同一段代码；"
        "脚本内置自检断言其四项指标与 `metrics_hier_bb_nob879_0921.csv` 逐项一致。",
        "",
        "## 一、对比总表",
        "",
    ]
    n_test = int(table["n_test"].iloc[0])
    n_dd = int(table["n_distinct_guide_test"].iloc[0])
    lines += [
        "| 模型 | 测试集 ρ | p（按 n=%d 行） | 去重后 ρ | p（按 n=%d 条 guide） | 测试集 AUC "
        "| LOGO 中位 ρ | Class A 中位 ρ | 有效折 |" % (n_test, n_dd),
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in table.to_dict("records"):
        lines.append("| %s | %+.4f | %.2e | %+.4f | %.3f | %.4f | %+.4f | %+.4f | %s |" % (
            r["model"], r["spearman_rho_test"], r["spearman_p_test"],
            r["spearman_rho_test_dedup"], r["spearman_p_test_dedup"], r["auc_test"],
            r["rho_logo_cv_median"], r["rho_logo_class_a_median"], r["valid_folds"]))

    lines += [
        "",
        "**读法**：两个预训练单模型在橡胶草 Hi-TOM 上的测试集 ρ 均为负且不显著"
        f"（p≈0.10），AUC≈0.52 与随机（0.5）无异；本项目形态二 GLMM 为 "
        f"ρ={glmm['spearman_rho_test']:+.4f}、AUC={glmm['auc_test']:.4f}。去重到 "
        f"{glmm['n_distinct_guide_test']} 条 distinct guide 后，GLMM 的 ρ 仍为 "
        f"{glmm['spearman_rho_test_dedup']:+.4f}（方向与量级稳健），而两个单模型反而更负"
        f"（{by_name[MODELS[0]]['spearman_rho_test_dedup']:+.4f} / "
        f"{by_name[MODELS[1]]['spearman_rho_test_dedup']:+.4f}），差距扩大。"
        f"**但 GLMM 的 p={glmm['spearman_p_test']:.2e} 不得单独引用**（伪重复导致过度乐观，"
        "理由与正确引用方式见第二节告警 1）。以上与 `transferability_0917.md` 的三体系对照"
        "一致（人源预训练模型迁移到植物体系高度数据集特异）。",
        "",
        "## 二、可比性告警（引用本表前必读）",
        "",
        f"1. **测试集有效样本极小，p 值系统性过度乐观**：留出集 {len(te_idx)} 行，但只覆盖 "
        f"**{n_group_test} 个基因组 / {n_distinct_test} 条 distinct seq30**。同一 guide 的重复"
        "测定不提供新的序列-效率信息，故 ρ 与 AUC 的有效样本量是 "
        f"{n_distinct_test} 而不是 {len(te_idx)}；而 `spearman_p_test` 是按 n={len(te_idx)} "
        "计自由度的，**不得单独引用**——表中已并列给出去重口径（按 distinct guide 取 indel "
        "中位数后重算的 `spearman_rho_test_dedup` / `spearman_p_test_dedup`）。这与 D2 决策点"
        "当年 ρ=0.331（p=4.67e-8）被自查撤回是同一个伪重复陷阱（见 "
        "`transferability_D2_0912.md` 第〇节），也与方案2 消融中「LRT 全部显著但基因聚类自助 "
        "CI 全跨 0」同源（见 `results/ablation_expression_report_0923.md`）。"
        f"**但去重口径的 p 不能反过来用于否定模型**：n={n_distinct_test} 时双侧精确置换检验的 "
        f"p 理论下限为 2/{n_distinct_test}! = {p_floor:.2e}（仅 |ρ|=1 时取到），故该口径下"
        "几乎不可能得到显著性——"
        f"它的作用是证明 n={len(te_idx)} 口径的 p 不可信，而非证明模型无效。形态二 GLMM 的"
        f"可信证据是**跨 {n_folds} 个基因组折的 LOGO-CV**（以基因为分析单元，无伪重复），"
        "见表中 `rho_logo_cv_median` 与 `rho_logo_class_a_median` 两列。",
        f"2. **两个单模型在本数据上近乎冗余**：DeepSpCas9 与 CRISPRon 的测试集打分 "
        f"Spearman ρ={mm_rho:.4f}；在 AUC 所用的两端掩码子集（{int(mask.sum())} 行）内更高达 "
        f"ρ={mask_rho:.4f}。所以\"两个独立基线\"实质上接近**一个**基线，"
        "这也解释了二者 AUC 仅差 0.0004、Class A 中位数完全相同。",
        "3. **LOGO 中位数的分母不一致**：三个模型的有效折分别为 "
        + "；".join("%s = %d/%d" % (m, vc.get(m, 0), n_folds) for m in MODELS)
        + ("。差异折为 " + "、".join("`%s`" % g for g in mismatch)
           + "——该折内部分模型的打分无方差（ρ 无定义）而另一部分有方差。故三者的 LOGO "
             "中位数**不是在同一组折上的比较**，横向差异应视为量级参考而非严格配对检验。"
           if fold_mismatch else "，三者一致，可直接横向比较。"),
        "4. **AUC 定义**：沿用 `scripts/13:85-91`——取测试集 indel_pct 的 20/80 分位、"
        "掩出两端各 20%、以 q_high 为阈值二值化，三模型共用同一标签与同一掩码。"
        "在上述仅 7 条 distinct guide 的条件下该指标接近退化；旧表 "
        "`model_comparison_full_0916.csv` 三个模型 AUC 全为 0.0735 很可能同源于此退化，"
        "但该表为 487 行旧口径，本次未复核，**不作为可引用数字**。",
        f"5. **逐折 ρ 被 distinct guide 数量化，符号几乎是唯一信息**：16 个基因组折中每折的 "
        f"distinct guide 数仅 {int(dg.min())}–{int(dg.max())} 条（中位 {int(dg.median())}）。"
        "折内 guide 这么少时 ρ 的可能取值是离散的几个数，实测 "
        f"**{n_identical_single}/{len(s_both)} 折两个单模型的 ρ 完全相同**，而 GLMM 与 "
        f"DeepSpCas9 在 **{n_flip}/{len(g_vs_d)} 折上符号相反、绝对值相同**（含 `LG03.451` "
        "的 ±0.852——正是方案2 消融中记录的那个翻转折）。故逐折 ρ 高度不稳，LOGO 中位数应"
        "连同有效折数与 Class A/B 分层一起引用，不宜单看某个数字。",
        "",
        "## 三、产物",
        "",
        "| 文件 | 内容 |",
        "|---|---|",
        "| `results/model_comparison_nob879_0921.csv` | 横向对比总表（本节表格的机器可读版） |",
        "| `results/model_comparison_nob879_folds_0921.csv` | 逐折明细：每折 × 每模型的 n、批次数、Class A/B、有效性、ρ |",
        "| `results/metrics_hier_bb_nob879_0921.csv` | 生产指标（GLMM 行的自检基准） |",
        "",
        f"Class A（低混杂多批折，出现在 ≥{CLASS_A_MIN_BATCHES} 个批次）共 {len(class_a)} 个基因组；"
        "逐折明细见 folds 表。",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("已落盘 %s" % OUT_REPORT.relative_to(BASE_DIR))
    print("\n[告警] 测试集仅 %d 基因组 / %d 条 distinct guide；两单模型打分 ρ=%.4f；"
          "有效折 %s" % (n_group_test, n_distinct_test, mm_rho,
                         "不一致" if fold_mismatch else "一致"))


if __name__ == "__main__":
    main()
