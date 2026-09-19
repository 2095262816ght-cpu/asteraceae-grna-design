"""06: Stacking 岭回归元模型训练与评估，骨架见 A4/A5 节。

防泄漏纪律：按 gene_id 分组划分（绝不随机切分）；alpha 只在训练集内调；
主指标 Spearman ρ，副指标 AUC（top20%/bottom20% 标签，Chen2022 做法）。
达标线：测试集 ρ >= 0.5。
"""
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit, LeaveOneGroupOut

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

df = pd.read_csv("results/feature_matrix_0914.csv")  # 9.14 冻结版
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_"))
         or c in ("tm", "poly_t")]
X, y, groups = df[FEATS].astype(float).values, df["efficiency_norm"].astype(float).values, df["gene_id"].values

# 外层：按基因分组 8:2（random_state=42 全队统一）
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr, te = next(gss.split(X, y, groups))
assert len(set(groups[tr]) & set(groups[te])) == 0, "训练/测试集基因泄漏！"
print(f"Train samples: {len(tr)} ({len(set(groups[tr]))} genes), Test samples: {len(te)} ({len(set(groups[te]))} genes)")

# 内层：仅训练集内 GroupKFold 调 alpha (转为 list 避免生成器耗尽)
cv_splits = list(GroupKFold(min(5, len(set(groups[tr])))).split(X[tr], y[tr], groups[tr]))
gs = GridSearchCV(Ridge(solver="svd"),   # cholesky 在本环境硬崩(exit 127)，svd 数值等价 {"alpha": np.logspace(-3, 3, 13)},
                  cv=cv_splits,
                  scoring="neg_mean_squared_error")
gs.fit(X[tr], y[tr])
best = gs.best_estimator_
best_alpha = gs.best_params_["alpha"]
print("Best alpha:", best_alpha)

# 测试集评估：集成 vs 单模型 Spearman rho
pred_ens = best.predict(X[te])
rho_ens, _ = spearmanr(pred_ens, y[te])
rho_deep, _ = spearmanr(df["deepspcas9_score"].values[te], y[te])
rho_crisp, _ = spearmanr(df["crispron_score"].values[te], y[te])

print(f"Stacking ensemble test rho: {rho_ens:.4f}")
print(f"DeepSpCas9 single test rho: {rho_deep:.4f}")
print(f"CRISPRon single test rho:   {rho_crisp:.4f}")

# 测试集评估：AUC (top20% vs bottom20% 二分类，Chen2022 做法)
y_te = y[te]
q_low = np.percentile(y_te, 20)
q_high = np.percentile(y_te, 80)
mask = (y_te <= q_low) | (y_te >= q_high)
if len(np.unique(y_te[mask] >= q_high)) > 1:
    y_bin = (y_te[mask] >= q_high).astype(int)
    auc_ens = roc_auc_score(y_bin, pred_ens[mask])
    auc_deep = roc_auc_score(y_bin, df["deepspcas9_score"].values[te][mask])
    auc_crisp = roc_auc_score(y_bin, df["crispron_score"].values[te][mask])
else:
    auc_ens, auc_deep, auc_crisp = np.nan, np.nan, np.nan

print(f"AUC test: Stacking={auc_ens:.4f}, DeepSpCas9={auc_deep:.4f}, CRISPRon={auc_crisp:.4f}")

# LOGO-CV (留一基因交叉验证，9.16 产物)
logo = LeaveOneGroupOut()
logo_rows = []
for tr_i, te_i in logo.split(X, y, groups):
    m = Ridge(alpha=best_alpha, solver="svd").fit(X[tr_i], y[tr_i])
    p_i = m.predict(X[te_i])
    # 常数折显式判定（round(6)，规避浮点尾差/浮点尘埃伪相关，见 docs/problem3.md 3.4）
    if len(set(np.round(y[te_i], 6))) > 1 and len(set(np.round(p_i, 6))) > 1:
        rho_i, _ = spearmanr(p_i, y[te_i])
    else:
        rho_i = np.nan
    logo_rows.append({"held_out_gene": groups[te_i][0], "n_samples": len(te_i), "rho": rho_i})

logo_df = pd.DataFrame(logo_rows)
logo_df.to_csv("results/logo_cv_0916.csv", index=False)
logo_median = logo_df["rho"].dropna().median() if not logo_df["rho"].dropna().empty else np.nan
print(f"LOGO-CV median rho: {logo_median}")

# 产出对比表 results/model_comparison_0919.csv
comp_df = pd.DataFrame([
    {"model": "DeepSpCas9 单用", "spearman_rho_test": round(rho_deep, 4), "auc_test": round(auc_deep, 4), "rho_logo_cv_median": np.nan},
    {"model": "CRISPRon 单用", "spearman_rho_test": round(rho_crisp, 4), "auc_test": round(auc_crisp, 4), "rho_logo_cv_median": np.nan},
    {"model": "Stacking 岭回归 (本工作)", "spearman_rho_test": round(rho_ens, 4), "auc_test": round(auc_ens, 4), "rho_logo_cv_median": round(logo_median, 4) if pd.notna(logo_median) else np.nan},
])
comp_df.to_csv("results/model_comparison_0919.csv", index=False)
print("Saved results/model_comparison_0919.csv")

# 保存训练好的元模型
joblib.dump(best, "results/meta_model_ridge_0919.joblib")
print("Saved results/meta_model_ridge_0919.joblib")

# 画图 1：散点对比图 results/scatter_ensemble_vs_best_0919.png
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
ax1.scatter(pred_ens, y[te], color="#2b5c8f", alpha=0.7, s=45)
ax1.set_title(f"Stacking 岭回归元模型 (测试集)\nSpearman rho = {rho_ens:.3f}, AUC = {auc_ens:.3f}")
ax1.set_xlabel("Stacking 预测得分")
ax1.set_ylabel("Hi-TOM 实测突变率 (%)")
ax1.grid(True, linestyle="--", alpha=0.4)

ax2.scatter(df["crispron_score"].values[te], y[te], color="#2a8b57", alpha=0.7, s=45)
ax2.set_title(f"CRISPRon 最强单模型 (测试集)\nSpearman rho = {rho_crisp:.3f}, AUC = {auc_crisp:.3f}")
ax2.set_xlabel("CRISPRon 预测得分")
ax2.set_ylabel("Hi-TOM 实测突变率 (%)")
ax2.grid(True, linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("results/scatter_ensemble_vs_best_0919.png")
plt.close()
print("Saved results/scatter_ensemble_vs_best_0919.png")

# 画图 2：LOGO 箱线图
valid_rhos = logo_df["rho"].dropna()
if len(valid_rhos) > 0:
    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    ax.boxplot(valid_rhos, vert=True, patch_artist=True, boxprops=dict(facecolor="#e1f5fe", color="#0288d1"))
    ax.set_title("留一基因交叉验证 (LOGO-CV) Spearman rho 分布")
    ax.set_ylabel("Spearman rho")
    ax.set_xticklabels(["LOGO-CV 各基因折"])
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig("results/logo_cv_box_0916.png")
    plt.close()
    print("Saved results/logo_cv_box_0916.png")

print("=== 06: Stacking 训练与全部评估产物完成 ===")
