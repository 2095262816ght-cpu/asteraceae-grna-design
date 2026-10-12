# -*- coding: utf-8 -*-
"""13: 全量版 合并打分 -> 特征矩阵 -> Stacking 训练评估（逻辑同 05+06）。

与 05/06 的差异：
  - 输入为全量重建产物（487 行 / 14 基因，含 5712、6995/6999 等 9.15-9.16 更正数据）；
  - 分组键 gene_group：LG01.6995 与 LG01.6999 为同源拷贝（problem2.md 一.1），
    合并为同一分组，防同源泄漏；
  - 所有输出带 _full_0916 后缀，不覆盖 9.x 冻结产物。
注意：crispr 环境的 scipy 1.15.2 cholesky 路径（scipy.linalg.solve/dposv）在本机
硬崩（exit 127，无 traceback），Ridge 默认 solver="auto"→cholesky 会中招；
故统一显式指定 solver="svd"（岭回归解与 cholesky 数值等价）。
"""
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.features_common import seq_features  # noqa: E402

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SUFFIX = "full_0916"

# ---- 合并（05 前置，原 scores_merged 无脚本，这里补上）----
df = pd.read_csv("data/hitom/hitom_seq30_full_0916.csv")
deep = pd.read_csv("results/scores_deepspcas9_full_0916.csv")
crisp = pd.read_csv("results/scores_crispron_full_0916.csv")
df = df.merge(deep, on="guide_id", validate="1:1").merge(crisp, on="guide_id", validate="1:1")
df["note"] = df["note"].fillna("")
df.to_csv(f"results/scores_merged_{SUFFIX}.csv", index=False)

# ---- 特征（语义单点定义在 core.sequence_spec，经 seq_features 适配器产出）----
df = pd.concat([df, seq_features(df.seq30)], axis=1)
df.to_csv(f"results/feature_matrix_{SUFFIX}.csv", index=False)
print(f"特征矩阵: {df.shape[0]} rows x {df.shape[1]} cols")

# ---- 训练（同 06，分组键换 gene_group）----
# 同源拷贝合并为一组（防泄漏）
HOMOLOG = {"EVM.MODEL.LG01.6995": "EVM.MODEL.LG01.6995/6999",
           "EVM.MODEL.LG01.6999": "EVM.MODEL.LG01.6995/6999"}
df["gene_group"] = df["gene_id"].replace(HOMOLOG)

FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_"))
         or c in ("tm", "poly_t")]
# NA 检查只针对模型实际使用的列（cds_offset 等元数据列在基因组回退行为空属正常）
assert not df[FEATS + ["efficiency_norm"]].isna().any().any(), "特征/标签列存在 NA，查明原因后再冻结"
X = df[FEATS].astype(float).values
y = df["efficiency_norm"].astype(float).values
groups = df["gene_group"].values
print(f"样本 {len(df)}，基因分组 {len(set(groups))} 个")

# 外层：按基因分组 8:2（random_state=42 全队统一）
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr, te = next(gss.split(X, y, groups))
assert len(set(groups[tr]) & set(groups[te])) == 0, "训练/测试集基因泄漏！"
print(f"Train: {len(tr)} ({len(set(groups[tr]))} groups), Test: {len(te)} ({len(set(groups[te]))} groups)")
print("测试集基因:", sorted(set(groups[te])))

# 内层：仅训练集内 GroupKFold 调 alpha
cv_splits = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
gs = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)},
                  cv=cv_splits, scoring="neg_mean_squared_error")
gs.fit(X[tr], y[tr])
best = gs.best_estimator_
print("Best alpha:", gs.best_params_["alpha"])

pred_ens = best.predict(X[te])
rho_ens, _ = spearmanr(pred_ens, y[te])
rho_deep, _ = spearmanr(df["deepspcas9_score"].values[te], y[te])
rho_crisp, _ = spearmanr(df["crispron_score"].values[te], y[te])
print(f"Stacking ensemble test rho: {rho_ens:.4f}")
print(f"DeepSpCas9 single test rho: {rho_deep:.4f}")
print(f"CRISPRon single test rho:   {rho_crisp:.4f}")

y_te = y[te]
q_low, q_high = np.percentile(y_te, 20), np.percentile(y_te, 80)
mask = (y_te <= q_low) | (y_te >= q_high)
if len(np.unique(y_te[mask] >= q_high)) > 1:
    y_bin = (y_te[mask] >= q_high).astype(int)
    auc_ens = roc_auc_score(y_bin, pred_ens[mask])
    auc_deep = roc_auc_score(y_bin, df["deepspcas9_score"].values[te][mask])
    auc_crisp = roc_auc_score(y_bin, df["crispron_score"].values[te][mask])
else:
    auc_ens = auc_deep = auc_crisp = np.nan
print(f"AUC test: Stacking={auc_ens:.4f}, DeepSpCas9={auc_deep:.4f}, CRISPRon={auc_crisp:.4f}")

# LOGO-CV（留一基因分组）
logo = LeaveOneGroupOut()
logo_rows = []
for tr_i, te_i in logo.split(X, y, groups):
    cv_splits_i = list(GroupKFold(min(5, len(set(groups[tr_i])))).split(X[tr_i], y[tr_i], groups[tr_i]))
    gs_i = GridSearchCV(Ridge(solver="svd"), {"alpha": np.logspace(-3, 3, 13)},
                        cv=cv_splits_i, scoring="neg_mean_squared_error")
    gs_i.fit(X[tr_i], y[tr_i])
    pred_i = gs_i.best_estimator_.predict(X[te_i])
    rho_i, _ = spearmanr(pred_i, y[te_i]) if len(set(y[te_i])) > 1 else (np.nan, None)
    logo_rows.append({"held_out_gene": groups[te_i][0], "n_samples": len(te_i), "rho": rho_i})
logo_df = pd.DataFrame(logo_rows)
logo_df.to_csv(f"results/logo_cv_{SUFFIX}.csv", index=False)
logo_median = logo_df["rho"].dropna().median()
print(f"LOGO-CV median rho: {logo_median}")
print(logo_df.to_string(index=False))

comp = pd.DataFrame([
    {"model": "DeepSpCas9 单用", "spearman_rho_test": round(rho_deep, 4), "auc_test": round(auc_deep, 4), "rho_logo_cv_median": np.nan},
    {"model": "CRISPRon 单用", "spearman_rho_test": round(rho_crisp, 4), "auc_test": round(auc_crisp, 4), "rho_logo_cv_median": np.nan},
    {"model": "Stacking 岭回归 (本工作)", "spearman_rho_test": round(rho_ens, 4), "auc_test": round(auc_ens, 4),
     "rho_logo_cv_median": round(logo_median, 4) if pd.notna(logo_median) else np.nan},
])
comp.to_csv(f"results/model_comparison_{SUFFIX}.csv", index=False)
joblib.dump(best, f"results/meta_model_ridge_{SUFFIX}.joblib")
print(f"Saved results/model_comparison_{SUFFIX}.csv, results/meta_model_ridge_{SUFFIX}.joblib")

# 图：LOGO 箱线图
valid_rhos = logo_df["rho"].dropna()
if len(valid_rhos):
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.boxplot(valid_rhos, vert=True)
    ax.set_title("留一基因交叉验证 (LOGO-CV) Spearman rho 分布（全量 0916）")
    ax.set_ylabel("Spearman rho")
    ax.set_xticks([1])
    ax.set_xticklabels(["LOGO-CV 各基因折"])
    plt.tight_layout()
    plt.savefig(f"results/logo_cv_box_{SUFFIX}.png")
    print(f"Saved results/logo_cv_box_{SUFFIX}.png")
