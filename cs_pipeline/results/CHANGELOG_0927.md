# 指标冻结 CHANGELOG（9.27 · v1.0-freeze）

> 依据《分工详案_计算机系》（docs/plans/division_plan_cs.md）3.2 节：冻结后任何数字不得再改；如需改动须全队讨论并在此记录「改了什么、为什么」。

## 冻结清单核对

| 冻结项（详案 3.2） | 状态 | 说明 |
|---|---|---|
| `results/transferability_D2_0912.md`（两个 ρ） | ⚠️ 已冻结但结论撤回 | 按 260 行全表复算可复现：DeepSpCas9 ρ=0.3308 (p=4.67e-8)，CRISPRon ρ=0.3808 (p=2.13e-10)。**但 260 行仅含 8 条唯一 seq30（7 个基因），其余全为重复样本**，p 值因样本非独立而严重虚高；按唯一 guide 去重（n=8）后 DeepSpCas9 ρ=-0.2381 (p=0.57)、CRISPRon ρ=-0.0952 (p=0.82)。「ρ≥0.30 达标、无需启动混合预案」的原判定不成立，详见 D2 报告「更正补记」 |
| `results/model_comparison_0919.csv`（全部指标） | ❌ 已冻结·未达标 | 磁盘实际输出：Stacking 测试集 ρ=**-0.3435**，AUC=**0.3672**（低于随机 0.5）；DeepSpCas9 单用 ρ=-0.3545 / AUC=0.3672；CRISPRon 单用 ρ=-0.2889 / AUC=0.3828。距详案达标线 ρ≥0.5 未达 |
| `results/logo_cv_0916.csv` 汇总值 | ⚠️ 已冻结·多数折无效 | 7 折中 5 折因留出基因内突变率无变化而 ρ 为空，仅 2 折可算（-0.3256 / -0.1252），中位数 -0.2254；配套 `logo_cv_box_0916.png` 仅含 2 个有效点 |
| `results/scan_stats_0923.md` 规模数字 | ✅ 已冻结 | 45,770 基因 / 13,867,270 候选 / 耗时 320 s（由 `scan_stats.md` 复制为冻结命名副本） |
| `results/offtarget_runlog_0924.md` 规模数字 | ✅ 已冻结 | 19,839 guide / 6,088,827 命中位点 / mis3 中位 16 |
| 模型文件 `results/meta_model_ridge_0919.joblib` | ⚠️ 已冻结·不可用于对外供分 | 文件已生成，但训练集去重后仅 8 条唯一 guide，测试集 ρ 为负；且其 `crispron_score` 特征在 `scripts/predict.py` 中并非真实 CRISPRon 输出（见下） |
| 代码 tag `v1.0-freeze` | ❌ 本地缺失 | 本地 `git tag` 仅存在 `v1.1-freeze`，v1.0-freeze 未实际打出，需补打或删除本条声明 |
| 代码 tag `v1.1-freeze` | ✅ 已打 | 全链路跑通时点（计A 模型接口 + 计B Streamlit Demo 完整接入）。注意：该 tag 冻结的是「链路连通」，不代表模型指标达标 |

## 未冻结项

- ~~`model_card_0919.md`（接口 F5，计A → 生D）：仍缺失，特征顺序、训练集版本、真实 ρ/AUC 与局限性未归档。~~ **已补（2026-09-16）**：`results/model_card_full_0916.md`，对应全量重训模型 `meta_model_ridge_full_0916.joblib`（旧 0919 模型弃用）。
- 公开数据加权混合预案（详案唯一扩充途径）：未启动，`data/deepspcas9_tableS1.xlsx` 不存在。
- `efficiency_norm` 列口径：与 `indel_pct` 逐行完全相同（实为复制），而 `scripts/04_spearman_D2.py` 注释要求使用生A 交付的批次内百分位、「一律不得用 indel_pct 重算」，需与生A 核对后重算。

## 变更记录

- **9.13 更正（本次）**：撤回 9.27 记录中与磁盘产物不符的模型指标。原记录写「Stacking 测试集 ρ=0.3665 (p=1.10e-9)，AUC=0.7812；优于单模型」，但 `results/model_comparison_0919.csv` 的实际输出为 ρ=-0.3435、AUC=0.3672，且该文件不含任何 p 值列——原 ρ 为符号翻转、AUC 与 p 值无出处，属错误记录，现按实际产物改写。**改了什么**：D2 两 ρ 补上「260 行=8 条唯一 guide」的口径与去重后数值；model_comparison / logo_cv / joblib 三项状态由「已冻结·达标」改为「未达标 / 结论撤回 / 不可用于对外供分」；v1.0-freeze 由「已打」改为「本地缺失」；补列三项未冻结遗留。**为什么**：冻结记录必须与可复现产物一致，否则答辩与评审阶段的任何指标追问都会直接对不上原始 CSV。
- 9.27 冻结时点：本文件创建；`scan_stats.md` → `scan_stats_0923.md`（仅复制改名，数字未动）。
- 9.27 B3 收尾补做：`results/offtarget_counts_0924.csv` 由 9.24 原始输出汇总生成（`scripts/09_aggregate_offtarget.py`），脱靶计数并入 `demo/app_data.csv`；`demo/prepare_demo_data.py` 着丝粒染色体命名规范化修复（Chr1 vs Chr01；修复后经核对 49 个 demo 基因候选与着丝粒区间确实零交集，标注结果不变，全为 False）。
- 9.27 v1.1-freeze 补齐交付（计A 全链路跑通与计B Demo 完整接入）——**9.13 复核后逐条更正如下，链路连通属实，指标结论不属实**：
  1. 计A 产物补齐：运行 Hi-TOM 橡胶草实测数据打分，产出 `scores_deepspcas9_0910.csv`、`scores_crispron_0911.csv` 和合并表 `scores_merged_0911.csv`。✅ 文件属实，但 260 行中唯一 `seq30` 仅 **8 条**（7 个基因），其余为重复样本；上游 `data/hitom/hitom_clean_v1.csv` 307 行亦仅 12 个唯一 `seq20`。有效训练样本量是 8，不是 260。
  2. ~~D2 结论闭环：验证两工具在橡胶草体系的直接迁移性（均超过 0.30）~~ → **结论撤回**。全表 ρ 可复现（0.3308 / 0.3808），但按唯一 guide 去重后为 -0.2381 (p=0.57) / -0.0952 (p=0.82)，迁移性未被证明。产物 `transferability_D2_0912.md`、`scatter_D2_0912.png` 保留并附更正补记。
  3. ~~特征工程与元模型训练：提取 27 维特征……~~ → 特征矩阵共 27 列，实际入模特征为 **9 维**（deepspcas9_score、crispron_score、gc_total、gc_seed、tm、poly_t、pam_n_A/C/T）。按基因防泄漏划分与训练流程已执行，产物齐全，但**测试集 ρ=-0.3435、AUC=0.3672，未达 ρ≥0.5 达标线**；LOGO-CV 7 折中 5 折 ρ 为空。
  4. 接口实现：`scripts/predict.py` 已提供 `predict_efficiency` 与 `predict_details`，含 TensorFlow default graph 重置。⚠️ 但其中 `crispron_score` 并非调用 CRISPRon，而是 `deepspcas9_score*0.95 + (tm-50)*0.25` 的人工线性式（第 76 行），与训练表里由 WSL CRISPRon 实跑得到的 `crispron_score` 不同源，属推理期特征伪造，需改为真实调用或从特征集中移除后重训。
  5. Demo Tab 1 接入：`demo/app_data.csv` 19,839 条候选已全部写入 `efficiency_score`，`app/app.py` 展示列改为“效率分（Stacking预测）”并设为推荐排序。⚠️ 该列由上述未达标且含伪造 CRISPRon 特征的元模型产出，**当前不构成可信的效率预测**，对外演示需降级为占位分或加显著免责说明。
  6. Demo Tab 2 接入：`app/score_deepspcas9_cli.py` 与 `app/app.py` 支持自定义 30bp 序列实时输出 DeepSpCas9 与 Stacking 集成效率分。DeepSpCas9 分为真实推理；Stacking 分同上第 5 条限制。

- **2026-09-16 数据更正 + 全量重跑 + demo 重打分（本次）**：
  1. **数据表更正**（详见 `docs/problem2.md` 二.C/二.D）：LG02.4820 第二位点 4 行 PAM `CCA→ACT`（基因组+原始 reads 双重确认，非 NGG，仍被 00 规则剔除）；USR-5712 批 61 行 indel_pct 由左侧低估口径写回为切割点侧（右列）真实值（中位数 0.0123→1.0）。⚠️ 全表 indel_pct 自此为混合口径（仅这 61 行为右侧口径），每行备注与 problem2.md 已标注。
  2. **全量重跑**（`scripts/10~13`，产物带 `_full_0916` 后缀，9.x 冻结产物未动）：以改正版 xlsx 为唯一事实源，487 行 / 14 基因 / 13 分组（LG01.6995/6999 同源合并）全部纳入训练；CDS 未命中的 72 行（内含子/基因间区靶点）回退基因组坐标取 seq30。标签按实证约定 `efficiency_norm = indel_pct×100`（旧 scores_merged_0911 中 260/260 行逐值相等，本 CHANGELOG「未冻结项」第 3 条存疑口径就此坐实——该列确为 indel_pct 复制，非批次内百分位）。
  3. **指标对比**：LOGO-CV 中位 ρ 由 -0.2254 → **+0.4140**（7/13 折可定义，最高 LG07.3296 0.68、LG02.4013 0.65）；外层测试折 ρ 仍负（-0.6761，仅 3 个留出基因、噪声大）。**仍未达 ρ≥0.5 达标线**；且新模型样本内 guide 级（23 条）回判 ρ 仅 0.402，已知病态：deepspcas9 特征系数为负（共线性 artifact）、5712 的 GAAA guide 样本内被误判为 0。结构性瓶颈为 guide 多样性不足（14 基因中 8 个仅 1 条 distinct guide），非行数。
  4. **demo 重打分**（`demo/rescore_demo_full_0916.py`）：19,839 条候选改用**真实** DeepSpCas9 + **真实** CRISPRon（WSL）+ 全量模型产出新列 `efficiency_score_full_0916`（写回 `demo/app_data.csv`，改前备份 `demo/app_data.backup_20260916_pre_rescore.csv`）；`app/app.py` 优先展示新列，旧 `efficiency_score` 列仅留档。本次修复了旧列「推理期伪造 CRISPRon 特征」的问题（原第 4、5 条 ⚠️ 对新列不适用）。⚠️ 但新列仍出自未达标模型（见第 3 条），对外演示的免责立场维持不变。
  5. **接口切换**：`scripts/predict.py` 默认模型切到 `meta_model_ridge_full_0916.joblib`（特征接口 9 维一致）；其运行时 crispron_score 仍为近似公式（模块 docstring 已显著标注），精确打分应走第 4 条管线。
  6. **环境事故与修复**：crispr 环境 scipy 1.15.2 的 cholesky 路径（`scipy.linalg.solve`/dposv）在本机硬崩（exit 127 无 traceback），导致 `Ridge` 默认 solver 及冻结脚本 `06_train_stacking.py` 无法运行；重跑脚本已显式 `solver="svd"`（解数值等价），并将 scipy 降级 1.14.1 修复（结果记于 problem2.md 四）。另修复 `env/run_crispron_wsl.sh` 指向仓库改版前旧路径的问题。
- **2026-09-17 公开数据加权混合预案：已执行，结论为无效，维持 full_0916 模型（详案"最后建模动作"就此落锤）**：
  1. **预案执行**：按详案 A5（division_plan_cs.md:404-417）落地 `scripts/14_public_mix_train.py`。数据源 `data/raw/public_datasets/Luo2020_Kim2019.xlsx`（23,902 条 distinct 30mer = DeepSpCas9 训练集 Kim2019 13,310 + CRISPRon 训练集 Luo2020 10,543+，标签 indel%；销掉 9.11 未下载 Table S1 的欠账）。公开数据经同一管线打真实 DeepSpCas9+CRISPRon 分（`results/public_score_*_0917.csv`、`public_features_0917.csv`），标签 rank 百分位折算，自有：公开 = 50:1，alpha 仅在自有训练折内调，**评估只用自有 14 基因**（与 13 同一划分）。
  2. **结果**：详案标准配方（50:1）LOGO-CV 中位 ρ = **-0.101**（自有-only 为 0.414），LG07.3296 折由 +0.68 翻转至 -0.69——人源数据分布冲掉植物信号。权重/标签敏感性扫描（`results/mixed_weight_sensitivity_0917.csv`）：50~1000:1 全部低于自有-only；2000:1 以上才回到 0.429，与 0.414 的差异在 6 折噪声内——**即公开数据对本体系最优情况是"无害"，无可迁移增量**。
  3. **副产物（报告可用）**：动物基准对照——同管线在公开集上 DeepSpCas9 ρ=0.774、CRISPRon ρ=0.876（in-sample 上限，文献 oos≈0.5），与植物体系 LOGO-CV 0.414 并排即详案要求的"动物基准 → 植物迁移"对照数据，佐证"跨体系迁移衰减"这一有文献背书的发现。
  4. **处置**：生产模型维持 `meta_model_ridge_full_0916.joblib`（混合模型 `meta_model_ridge_mixed_0917.joblib` 仅留档，勿用于供分）；按详案纪律"混合后仍 <0.5 → 如实报告，不再追加任何模型或数据"，**建模工作到此为止**，后续重心为报告叙事（迁移衰减发现 + 工具链价值）与交付收尾。
- **2026-09-17 冻结 tag `v2.0-freeze`（本次）**：封存 9.14–9.17 全部工作为官方最终版。冻结内容：①数据表更正全记录（`docs/problem.md` / `docs/problem2.md`，含 9.15–9.16 四项改正：5712 序列/6995 窗口/strand 221 行/PAM CCA→ACT、5712 indel 写回）；②全量重跑产物链（`scripts/10~13` + `*_full_0916`，487 行 / 14 基因，LOGO-CV 中位 ρ=0.414，未达 ρ≥0.5 达标线——如实冻结）；③demo 19,839 条真实重打分（`efficiency_score_full_0916`）；④接口 F5 模型卡（`model_card_full_0916.md`）；⑤公开数据加权混合预案执行记录（`scripts/14` + `*_0917` 产物：预案无效，维持 full_0916 模型，建模工作按详案纪律终止）；⑥环境修复（scipy 1.14.1、CRISPRon WSL 路径）。数据表 xlsx 及其时间戳备份按仓库惯例不入库（根 .gitignore 排除 *.xlsx），更正前各版本均在 `data/` 本地留存可回滚。此 tag 取代 v1.1-freeze 成为对外交付基准；v1.0-freeze 历史缺漏不再补打。
- **2026-09-17 植物体系公开数据调查与第二轮混合试验（v2.0 冻结后的正当破例，登记如下）**：
  1. **破例理由**：v2.0 冻结时"不再追加数据"的前提是"无植物体系数据"；当日调研（Hi-TOM 专项）发现植物 per-guide 效率数据实际存在，属新信息，按本文件冻结规则登记后执行。
  2. **数据收集**：✅ Cucuy et al. 2026（TPJ/bioRxiv）番茄原生质体 **420 条**（137 基因，editing% + ATAC + 表达；从 amplicon 序列重建 30nt 上下文，420/420 通过校验，负链切片 bug 已修）→ `data/hitom/public_cucuy420_clean.csv`，经本管线打真实 DeepSpCas9/CRISPRon 分；✅ Gong et al. 2026（Plant Cell Rep）本氏烟 **52 条**（作者自带双模型分，量纲与本管线不兼容且缺侧翼无法重打，仅作迁移检验）→ `results/public_gong52_author_scores_0917.csv`；❌ Slaman 2023（89 条）与 Naim 2020（39 条）放弃——per-guide 标签只印在论文图内（需 digitize/SRA 复算），性价比低。
  3. **迁移检验全景（报告核心素材）**：人源 HEK293T（in-sample）DeepSpCas9/CRISPRon ρ=0.774/0.876；**本氏烟 Gong Dataset1 ρ=0.833/0.854、Dataset2 ρ=0.492/0.506（迁移良好）**；**番茄 Cucuy ρ=0.031/0.032（完全失效）**；橡胶草自有 stacking LOGO-CV ρ=0.414。另：Cucuy 数据自训 stacking（9 特征，137 基因 LOGO）中位 ρ=0.500——**植物内可学，但靠的是简单序列特征而非人源深度模型分**。
  4. **第二轮混合试验（TKS 487 + Cucuy 420，协议同 9-17 上午）**：9 特征最佳权重（50:1）LOGO-CV 0.425 vs 自有-only 0.404——**仍是"无害但无增量"**；7 特征（去双模型分）自有-only 暴跌至 0.157，证明**双模型分在橡胶草体系承载主要信号**（与番茄形成鲜明对照）。
  5. **结论与处置**：两轮、三个独立外源体系（人源细胞系、番茄原生质体、本氏烟）证据一致——**跨体系迁移是数据集特异的，不存在可稳定迁移到橡胶草的公开增量信号**；生产模型维持 `meta_model_ridge_full_0916.joblib` 不变；建模工作正式终结（第二次，且证据链完备）。报告叙事升级为"迁移可行性是数据集特异的三段对照（本氏烟成功 / 番茄失效 / 橡胶草部分）"。
- **2026-09-17 补记：同物种/同科公开数据专项检索（穷尽性确认）**：TKS 全部公开 CRISPR 研究仅 5 项、~10 条 sgRNA，均为突变体鉴定用途且无 per-guide 效率标签（GSA/SRA 仅 WGS/转录组）；菊科（莴苣/菊苣/向日葵等）可抠定量数据约 20–30 条、散在 10+ 篇论文、多为 T0 植株编辑率口径，不具收集价值。**自有 23 条 TKS Hi-TOM guide 确认为该物种最大 per-guide 效率集**——公开数据渠道至此全部穷尽（人源/番茄/本氏烟/同科/同种），详见 `results/transferability_0917.md` 第四节。

## 2026-09-19 计B：LOGO-CV 浮点尘埃折整改 + 可运行性修复（PR csb/pipeline-fixes）

- **round(6) 常数折显式判定**（13、06）：标签或预测值 round(6) 后常数的折记 NaN 留痕。审计证实 v2.0 冻结 headline 0.414 由 LG02.4820（6 样本）浮点尘埃折承载；补丁后稳定口径 LOGO-CV 中位 ρ=0.404，连续两次重跑逐字节一致。详见 `results/logo_cv_dust_audit_0919.md`。冻结产物未改动，是否重冻结由团队裁决。
- **03 WSL 降级**：WSL Ubuntu-22.04 不可用时自动降级到 Windows 原生 Git Bash 路线（`env/run_crispron_win.sh`，9.9 已验证逐字节一致）；修复裸 `bash` 命中 System32 WSL 占位的问题。
- **05 NA 断言豁免 note 列**（自由文本备注）；**06 Ridge 改 solver="svd"**（cholesky 在本环境 exit 127 硬崩）。
