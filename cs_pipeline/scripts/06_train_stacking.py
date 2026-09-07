"""06: Stacking 岭回归元模型训练与评估，骨架见 A4/A5 节。

防泄漏纪律：按 gene_id 分组划分（绝不随机切分）；alpha 只在训练集内调；
主指标 Spearman ρ，副指标 AUC（top20%/bottom20% 标签，Chen2022 做法）。
达标线：测试集 ρ >= 0.5。
"""
import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, GroupKFold, GroupShuffleSplit

df = pd.read_csv("results/feature_matrix_0914.csv")  # 9.14 冻结版
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_"))
         or c in ("tm", "poly_t")]
X, y, groups = df[FEATS].values, df["efficiency_norm"].values, df["gene_id"].values

# 外层：按基因分组 8:2（random_state=42 全队统一）
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr, te = next(gss.split(X, y, groups))
assert len(set(groups[tr]) & set(groups[te])) == 0, "训练/测试集基因泄漏！"

# 内层：仅训练集内 GroupKFold 调 alpha
gs = GridSearchCV(Ridge(), {"alpha": np.logspace(-3, 3, 13)},
                  cv=GroupKFold(5).split(X[tr], y[tr], groups[tr]),
                  scoring="neg_mean_squared_error")
gs.fit(X[tr], y[tr])
best = gs.best_estimator_
print("best alpha:", gs.best_params_["alpha"])

# 测试集：集成 vs 单模型
pred_ens = best.predict(X[te])
rho_ens, _ = spearmanr(pred_ens, y[te])
print(f"Stacking ensemble: rho = {rho_ens:.3f}")
for name, col in [("DeepSpCas9", "deepspcas9_score"), ("CRISPRon", "crispron_score")]:
    rho_single, _ = spearmanr(df[col].values[te], y[te])
    print(f"{name} single:    rho = {rho_single:.3f}")

# TODO(A5): AUC 分支（top20/bottom20）、LOGO-CV（results/logo_cv_0916.csv）、
#           对比表 results/model_comparison_0919.csv
joblib.dump(best, "results/meta_model_ridge_0919.joblib")
