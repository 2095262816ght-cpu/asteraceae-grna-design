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
- ~~公开数据加权混合预案（详案唯一扩充途径）：未启动，`data/deepspcas9_tableS1.xlsx` 不存在。~~ **已执行并终结（2026-09-17，两轮）**：Table S1 未直接下载，但等价数据已入库（`data/raw/public_datasets/Luo2020_Kim2019.xlsx`，23,902 条 = DeepSpCas9 训练集 Kim2019 + CRISPRon 训练集 Luo2020）；第一轮人源混合与第二轮植物数据（番茄 Cucuy 420）混合均"无害但无增量"，公开渠道穷尽，建模按详案纪律终结——见下方 9.17 各条变更记录。
- `efficiency_norm` 列口径：与 `indel_pct` 逐行完全相同（实为复制），而 `scripts/04_spearman_D2.py` 注释要求使用生A 交付的批次内百分位、「一律不得用 indel_pct 重算」，需与生A 核对后重算。

## 变更记录

- **2026-10-10 模型卡文档更正 + 形态二敏感性诊断（诊断件登记；冻结指标不改）**：
  1. **改了什么**：`model_card_hier_bb_nob879_0921.md` §5 过离散度参数由「s ≈ 20.08」更正为落盘实测 `dispersion_s = 0.632`（20.08 实为拟合初值 e³ 的误写）；并注明 `hier_bb_model.py` 的 `clamp(1.0, 500)` 使其生效值为 1.0（该参数化允许的过离散上限），Beta-Binomial 层在本数据上近似退化为二项。**为什么**：冻结文档数字必须与可复现产物一致（同 9.13 更正原则）。
  2. **敏感性诊断**（新增 `scripts/dev/sensitivity_glmm_1010.py`，产物 `results/sensitivity_glmm_1010.md` + 3 个 CSV）：2×2（先验{全量, 折内重算} × s_floor{1.0, 0.01}），其余与 scripts/15 逐位同协议——
     - **先验泄漏**（scripts/15:56 的 `compute_batch_prior` 在全量 879 行上估计、测试集与各 LOGO 折共用，测试折标签经 u_prior 进入训练）：折内重算后 LOGO 中位 +0.3716→+0.3635、Class A 中位 +0.4636 不变（核心结论稳健）；**测试集 ρ +0.3424→−0.0642（对先验来源敏感）**——单一留出分割数字不稳健，对外引用以 LOGO/Class A 为准；
     - **s_floor**：放开下界后 s 收敛 0.9275（拟合想要 s≈0.9，恰在旧边界附近），β 最大变动 0.06、LOGO 中位 −0.02、测试集/Class A 不变——过离散层近似二项、指标不敏感；
     - **复现性**：同协议重跑 7/9 折与 0921 冻结逐折 ρ 逐位一致，LG05.2725 / LG07.3933 两折末位秩翻动（float32 LBFGS 跨环境数值漂移 × 每折仅 1–4 条 distinct guide 的秩量化噪声），印证"逐折 ρ 基本是符号信息"。
  3. **冻结指标处置**：`metrics_hier_bb_nob879_0921.csv` 与模型卡 ρ 数字不改（v2.1 冻结）；模型卡 §1/§4.1 的「彻底治愈崩溃」「真实生物学上限」措辞按上述敏感性软化为「留出集由负转正（对先验来源敏感）」「低混杂折上限估计」。
  4. **代码变更**：`hier_bb_model.fit_hierarchical_selective_bb` 新增 `s_floor=1.0` 默认参数（默认行为与 0921 产物逐值等价，scripts/15 不传参不受影响）；生产训练脚本改折内先验 / 放开 s 重训均属评估协议与模型变更，待全队决定（见 `results/sensitivity_glmm_1010.md` §4）。

- **2026-10-11 表述更正（过离散度叙事口径，非指标变更）**：10-10 条目及 `model_card_hier_bb_nob879_0921.md` §5、`results/sensitivity_glmm_1010.md` §2.3、答辩材料中的「Beta-Binomial 层近似退化为二项」表述**方向有误**，予以更正：生效 s=1.0 是 `clamp(1.0, 500)` 下界 = 该参数化允许的**过离散最大值**（s 越小过离散越大；s=1 时过离散因子 (n+1)/2，本数据 n≈50–3000，为二项方差的数十至千余倍），拟合想要更小的 s（自由拟合收敛 0.9275），并非二项退化。敏感性实验支持的结论是「**指标对 s 不敏感**（β 变动 ≤0.06、指标变动 ≤0.02）」，推不出二项性（检验二项性应对比 s=1 与 s→∞，实验未做）。同日已同步更正模型卡 §5、诊断件 §2.3 与 defense_03/06 表述；专利《技术交底书_v1_20261009》中「s ≈ 20.08」处加更正注（v2 修订时正式改）。

- **2026-09-29 工程变更（D 工单批次，参考包导入与三档百分位，非指标变更）**：
  1. **D1 参考包抽象（ReferenceBundle）**：莴苣/橡胶草升级为预置参考包（`reference_bundle_service.py`：基因组 FASTA + GFF + 表达矩阵 + 组织列映射统一形态），`species` 参数升级为 `bundle_id`（兼容保留）；新增 `reference_bundles` 表存用户导入包；纯 Python `.fai` 索引构建（免 samtools）；TKS evm.TU↔evm.model 规则映射与 S1–S9 时相逻辑泛化为包配置（`expression_id_rule` / `expression_layout`）。
  2. **D2 导入管线**：`GET/POST /api/v1/sequence/bundles`（清单/服务端路径注册）+ `POST /api/v1/sequence/bundles/upload`（≤50MB 小文件直传，大基因组走路径注册——离线部署 2.6GB FASTA 不适合浏览器上传）；注册前置校验（FASTA 可建 .fai、表达矩阵可解析且映射列存在、预置包 ID 禁覆盖）；前端 Tab 2「导入参考包」面板（路径 + 上传 + 组织列映射行编辑 + ID 规则选择）。
  3. **D3 三档效率百分位（口径逐行标注，不硬猜）**：① 库内该基因预计算候选分布（Tab 1 同源）→ ② **现场枚举同基因候选 + 批量打分**（`gene_candidate_service.py`：基因体+TSS 上游 2kb 双链 NGG 全枚举，同推理管线批量打分，rank(pct=True) 真·Tab 1 同口径，按基因+参考包缓存）→ ③ 贴入集合百分位（批内排名口径，非基因内，显著标注；单条无集合不排名）。custom 档未锚定也可按需算脱靶（相似位点计数），并逐条给出 `缺失原因`/`所需数据`；批量任务详情逐条派生 `batch_percentile`。
  4. **D4 导出缺啥写啥**：新增 `GET /api/v1/scoring/jobs/{job_id}/export`（批量/单条任务结果导出 xlsx/csv，前端批量卡一键导出），逐行携带 `效率百分位/百分位口径/多组学证据状态/缺失原因/所需数据/所用参考包`；Tab 1 实验设计导出同步增列（百分位口径=库内分布、所需数据逐行派生）；xlsx 附 `指标方法说明` 与 **`数据需求模板`** sheet（参考基因组/GFF/表达矩阵格式要求与缺失行为）。
  5. **D5 测试与文档**：新增 `test_reference_bundle_service.py`（4 例）、`test_scoring_job_export.py`（2 例）、`test_annotation_service.py` 扩至 11 例（三档百分位、贴入集合口径、custom 脱靶/不硬猜）；USER_MANUAL 3.5/3.6 更新（参考包导入、三档口径表、导出列说明）。**口径纪律**：未导入参考基因组/表达矩阵时导出与界面逐行标注「缺什么、需要什么数据」，绝不以 0 冒充未计算值。

- **2026-09-29 工程变更（A/B/C 工单批次，非指标变更）**：
  1. **A组（输入端全基因组）核查与收尾**：确认数据层已就绪（`lifescience.db` 已灌 46,030 基因 = 45,981 `LsT2T1G*` + 49 NLR `LsaT2T01G*`，候选 4,549,329 条，索引齐全；按基因查询实测 count≈1ms、top50≈5ms，达标 <5s）；`/api/v1/genes` 增加 `q`/`limit` 搜索限量参数；前端基因下拉修复 46k 选项全量渲染卡死问题（限显 200 条 + 提示）、修正非 NLR 基因误标「NLR」的 fallback、下拉项标注注释来源（全基因组注释 / NLR 专项注释）；README 输入端表述更新为全基因组口径。
  2. **A1 ID 口径结论（重要）**：两套 ID 不是同一注释的别名，而是**同一 T2T 坐标系下互补的两套注释**——`LsT2T1G*`（Liftoff 全基因组 45,981 个）与 `LsaT2T01G*`（NLR 专项 49 个，落在 Liftoff 注释缺口内，例：`LsaT2T01G023690` 位于 Chr01:83.87Mb，两侧 LsT2T 基因模型均缺失）；坐标重叠匹配仅 5/49 ≥0.5，且编号空间独立（同号 023690 在两套注释中位置不同）。**决策：不做 ID 互改/合并**，双命名空间共存，搜索两种 ID 均可，UI 按前缀标注注释来源。
  3. **B1 橡胶草自定义通道支持**：核查确认打分链路纯序列驱动、物种无关（`validate_seq30` → InferenceClient）；全栈单序列卡与 Streamlit Tab 2 增加「支持任意物种 30bp（橡胶草/莴苣等），v2.1 模型本为橡胶草 Hi-TOM 金标准训练」标注与局限声明（同基因内相对排序、非绝对 indel%）；批量导入模板新增橡胶草实测示例行（`Sample_TKS_01/02`，源自 Hi-TOM `EVM.MODEL.LG07.3296/3933` 真实位点）与物种支持说明。
  4. **C1–C3 Tab 2 功能补齐**：批量结果增加效率分阈值/排序键/Top-N 择优；新增效率分分布直方图、DeepSpCas9-效率分与 GC-效率分散点（echarts）；10 维特征向量展示（**单一来源 `features_common.seq_features`**，与训练/推理同口径；后端 `scoring_service`/`scoring.py` 暴露 `features` 与 `crispron_score`，批量行可展开特征）；`backend/requirements.txt` 补 `biopython>=1.81`（features_common 依赖）。
  5. **C4–C6 序列三态注释与按需多组学**：新增 `POST /api/v1/sequence/annotate`（`sequence_annotation_service.py`）——`precomputed`（seq30 命中预计算候选 → 复用 Tab 1 同源多组学列内嵌展示）、`annotated`（精确回贴莴苣 T2T/橡胶草基因组 → 注释基因座 + 按需脱靶 `offtarget_service.profile_seq20` + 按需方案3 优先指数，效率百分位用与 Tab 1 完全相同的 `rank(pct=True)` 并入该基因候选分布求取，公式复用 `multiomics_service.priority_scores`）、`custom`（未锚定 → 多组学如实标注「无法计算」不硬算）；前端单序列卡增加回贴基因组选择（莴苣/橡胶草）、三态结果卡与「计算脱靶+优先指数」按钮；TKS 命中经实测验证（`ATATGAAAATGTCAGGATGCCTGAAGGACA` → `evm.TU.LG07.3296`，LG07:109,028,891）。**TKS 表达 ID 体系核对结论与接入**：表达矩阵 `evm.model.X` 与 GFF `evm.TU.X` 为同一 EVM 体系 TU/model 前缀变体，locus 36,239/36,239 一一对应，按规则变换匹配（无需映射表）；TKS 命中现展示 S1–S9 时相表达（根/胶乳/叶阶段均值、峰值阶段、方案6 推荐转化窗口 S4，实测 LG07.3296 胶乳 S4 起 275、S6 峰 288 与窗口口径一致）；方案3 为莴苣 5 组织口径不适用橡胶草，表达项按 0 计并如实标注，不硬套。新增单测 `backend/tests/test_annotation_service.py`（5 例：三态 + 不硬猜纪律 + TKS 时相映射），隔离库全过。
  6. **测试纪律事故与新规（如实记录）**：本次开发中曾并发运行两轮 `backend/tests` 且中途终止其一，`test_candidates_api` 的清表夹具导致真实 `lifescience.db` 基因/候选/表达表被清空；已由 `seed_candidates_if_empty(force_reseed=True)` 从 CSV 全量恢复（路径 C + demo 双路）。**新规：backend 测试一律以 `DATABASE_URL=sqlite+aiosqlite:///./lifescience_test.db` 隔离运行，严禁对真实库执行测试套件**；测试夹具清表行为本身亦为遗留风险，建议后续改造为独立 fixture 库。

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
  1. **数据表更正**（详见 `docs/data-governance/problem2.md` 二.C/二.D）：LG02.4820 第二位点 4 行 PAM `CCA→ACT`（基因组+原始 reads 双重确认，非 NGG，仍被 00 规则剔除）；USR-5712 批 61 行 indel_pct 由左侧低估口径写回为切割点侧（右列）真实值（中位数 0.0123→1.0）。⚠️ 全表 indel_pct 自此为混合口径（仅这 61 行为右侧口径），每行备注与 problem2.md 已标注。
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
- **2026-09-17 冻结 tag `v2.0-freeze`（本次）**：封存 9.14–9.17 全部工作为官方最终版。冻结内容：①数据表更正全记录（`docs/data-governance/problem.md` / `docs/data-governance/problem2.md`，含 9.15–9.16 四项改正：5712 序列/6995 窗口/strand 221 行/PAM CCA→ACT、5712 indel 写回）；②全量重跑产物链（`scripts/10~13` + `*_full_0916`，487 行 / 14 基因，LOGO-CV 中位 ρ=0.414，未达 ρ≥0.5 达标线——如实冻结）；③demo 19,839 条真实重打分（`efficiency_score_full_0916`）；④接口 F5 模型卡（`model_card_full_0916.md`）；⑤公开数据加权混合预案执行记录（`scripts/14` + `*_0917` 产物：预案无效，维持 full_0916 模型，建模工作按详案纪律终止）；⑥环境修复（scipy 1.14.1、CRISPRon WSL 路径）。数据表 xlsx 及其时间戳备份按仓库惯例不入库（根 .gitignore 排除 *.xlsx），更正前各版本均在 `data/` 本地留存可回滚。此 tag 取代 v1.1-freeze 成为对外交付基准；v1.0-freeze 历史缺漏不再补打。
- **2026-09-17 植物体系公开数据调查与第二轮混合试验（v2.0 冻结后的正当破例，登记如下）**：
  1. **破例理由**：v2.0 冻结时"不再追加数据"的前提是"无植物体系数据"；当日调研（Hi-TOM 专项）发现植物 per-guide 效率数据实际存在，属新信息，按本文件冻结规则登记后执行。
  2. **数据收集**：✅ Cucuy et al. 2026（TPJ/bioRxiv）番茄原生质体 **420 条**（137 基因，editing% + ATAC + 表达；从 amplicon 序列重建 30nt 上下文，420/420 通过校验，负链切片 bug 已修）→ `data/hitom/public_cucuy420_clean.csv`，经本管线打真实 DeepSpCas9/CRISPRon 分；✅ Gong et al. 2026（Plant Cell Rep）本氏烟 **52 条**（作者自带双模型分，量纲与本管线不兼容且缺侧翼无法重打，仅作迁移检验）→ `results/public_gong52_author_scores_0917.csv`；❌ Slaman 2023（89 条）与 Naim 2020（39 条）放弃——per-guide 标签只印在论文图内（需 digitize/SRA 复算），性价比低。
  3. **迁移检验全景（报告核心素材）**：人源 HEK293T（in-sample）DeepSpCas9/CRISPRon ρ=0.774/0.876；**本氏烟 Gong Dataset1 ρ=0.833/0.854、Dataset2 ρ=0.492/0.506（迁移良好）**；**番茄 Cucuy ρ=0.031/0.032（完全失效）**；橡胶草自有 stacking LOGO-CV ρ=0.414。另：Cucuy 数据自训 stacking（9 特征，137 基因 LOGO）中位 ρ=0.500——**植物内可学，但靠的是简单序列特征而非人源深度模型分**。
  4. **第二轮混合试验（TKS 487 + Cucuy 420，协议同 9-17 上午）**：9 特征最佳权重（50:1）LOGO-CV 0.425 vs 自有-only 0.404——**仍是"无害但无增量"**；7 特征（去双模型分）自有-only 暴跌至 0.157，证明**双模型分在橡胶草体系承载主要信号**（与番茄形成鲜明对照）。
  5. **结论与处置**：两轮、三个独立外源体系（人源细胞系、番茄原生质体、本氏烟）证据一致——**跨体系迁移是数据集特异的，不存在可稳定迁移到橡胶草的公开增量信号**；生产模型维持 `meta_model_ridge_full_0916.joblib` 不变；建模工作正式终结（第二次，且证据链完备）。报告叙事升级为"迁移可行性是数据集特异的三段对照（本氏烟成功 / 番茄失效 / 橡胶草部分）"。
- **2026-09-17 补记：同物种/同科公开数据专项检索（穷尽性确认）**：TKS 全部公开 CRISPR 研究仅 5 项、~10 条 sgRNA，均为突变体鉴定用途且无 per-guide 效率标签（GSA/SRA 仅 WGS/转录组）；菊科（莴苣/菊苣/向日葵等）可抠定量数据约 20–30 条、散在 10+ 篇论文、多为 T0 植株编辑率口径，不具收集价值。**自有 23 条 TKS Hi-TOM guide 确认为该物种最大 per-guide 效率集**——公开数据渠道至此全部穷尽（人源/番茄/本氏烟/同科/同种），详见 `results/transferability_0917.md` 第四节。
- **2026-09-18 ~ 09-21 数据扩表、老师裁决落地与 16.1 版交付链（9.21 登记；v2.0 冻结后的数据治理工作，生产模型未动）**：
  1. **9.18 扩表**：NEWdata 17 批次 877 行并入主表 → `1_Hi-results-13-merged-20260918.xlsx`（1368 行 / 24 批次；过程见 `docs/data-governance/problem3.md`）；模型输入 `data/hitom/hitom_seq30_merged_0918.csv`（1361 行可打分，7 行无 seq-20/非 NGG 无分）。同日两口径重跑：merged 全表（813 行）LOGO-CV 中位 ρ=-0.257、confident（544 行）ρ=+0.247（`logo_cv_{merged,confident}_0918.csv`）——未剔 QC 的全表噪声主导，实证"堆行数无效"。
  2. **9.19 老师裁决与独立审计**：裁决 = `excluded_gids_final_0919.csv`（360 gid：QC 口径 253 + USR-14333 整批 87「疑 T2 代测序」+ USR-22807 整批 20「参照与基因型不配套」；USR-5448「杂合子材料」/ USR-6137 QC 撤销恢复保留）。⚠️ 裁决无原始凭证文件（同学回传的"(4).xlsx"经 md5 验证为 13-merged 重复下载副本、无批注），书面记录待补要。计B 独立审计 `b_audit_0919.md`；1005 行锚定重跑：raw LOGO -0.262 → 批次偏移锚定 -0.079（`b_anchor_final_0919.csv`）；敏感性：487 行基线 0.404，去 indel=1 的 101 行 → 0.596，去 USR-8145 → 0.477（`b_sensitivity_logo_0919.csv`）——**0.414 级数字对行口径高度敏感**。
  3. **9.20 同学交付 14/15 版**：A/B/D 证据分级 + 置信分（规则 7 条）、效率分 4 列，训练集 939 行。**9.21 独立审计（`b_audit_0920.md`）发现两个阻断问题**：B1 效率综合分含未记载的 0.1 tie-break 抖动（975 行仅 38 个 distinct 分数对，最大并列组 243 行被摊到 25.7 分跨度、306 个名次）；B2 9.19 裁决未落地（打分只读了 0918 基表备注列：28 行裁决剔除被误保留、94 行裁决保留被误剔，939 ≠ 1005 口径）。
  4. **9.21 修正版 16/16.1**：`b_fix_16_postruling_0921.py`（裁决落地 + 效率分去抖动 + 裁决回写备注列 174 行）+ `b_fix_161_pending_grades_0921.py`（guide候选表回传后 22 行"待定"补定级：16 行 refM Top1=68077→A/80，6 行 refSP1 Top1=62→弱信号 D/25）。**现行交付版 `data/1_Hi-results-16.1-efficiency-20260921.xlsx`：1368 = 训练集 969 + 保留-不可打分 3 + 剔除(9.19裁决) 360 + 剔除(弱信号,待老师追认) 36**（969+36=1005 与裁决口径闭环）。交叉核对 `b_crosscheck_0921.py`：guide候选表（61 条/35 ref）对 15 版 219 行规则 2/3/4 分级复推 219/219 一致、判定依据引用热点分数 0 不符；14→15 谱系 18 列 0 差异；15 版 push 副本与本地审计副本逐格一致。
  5. **9.21 评估重跑（16.1 口径，`b_anchor_161_0921.csv`）**：ruling1005 复现 0919（raw -0.220 / anchor -0.078，浮点噪声级）；**train969：raw -0.248 / 锚定 LOGO-CV 中位 ρ=+0.310（12/17 折）= 现行数据口径最好数字**；noB879（去 B 级 90 行）：anchor +0.297，B 级影响小。**剔弱信号 36 行使锚定 LOGO -0.078 → +0.310**（身份不明 guide 的 seq-20 属特征噪声源）——弱信号剔除的实证支持，随本条交老师追认（追认结果决定训练集 969 / 1005）。ρ≥0.5 达标线在所有口径下仍未达到。
  6. **编号地雷处置**：`scores_merged_merged_0918.csv` / `feature_matrix_merged_0918.csv`（813 行）的 guide-id 编号与主表/hitom 不一致（例：TKS_0795 在其为 USR-5448/ACAATAACAGACGCCGCCGG，在主表为 USR-4811/GGCGTTAGATTGACAGAAGA），按 guide-id 跨文件 join 会静默拼错数据——两文件已改名加 `_DEPRECATED` 后缀留档（0918 LOGO 数字复现仍需用它们，但只能按行内自带序列使用）。1361 行的 `scores_{deepspcas9,crispron}_merged_0918.csv` 与主表同编号，现行可用。
  7. **NEWdata 目录归并（9.21）**：经 MD5 全量核对，唯一文件并入 `data/raw/hitom/NEWdata_0918/`（18 个批次 xls + 138 个 USR-23709 原始 fastq 唯一拷贝 + 5 个旧批次唯一 xls），纯冗余删除（138 个逐文件验证相同的备份 fastq + 4 个与 data/raw 字节级相同的 xls）；`NEWdata/` 撤销，归并记录见该目录 README。
  8. **生产模型与冻结边界（⚠️ 需全队决策会签）**：v2.0-freeze 的生产模型 `meta_model_ridge_full_0916.joblib`（487 行、裁决前口径）此前留存未动；本条第 1–5 款全部为扩表与裁决后的数据治理与评估重跑。是否按 16.1 口径重训并重新冻结，按本文件冻结规则须全队讨论决定。
  9. **生产模型架构与训练集终版决议（2026-09-21 会签定案，第 8 款决策点正式闭环）**：
     - **数据口径定案**：正式剔除 16.1 训练集中 90 行“多候选竞争未经设计表确认”的 B 级脏数据，确定以 **`noB879`（879 行纯 A 级金标准）** 作为新一代官方生产与科研基准训练集。
     - **模型架构定案**：正式采纳**形态二（分层选择性 Beta-Binomial GLMM，A1 + A2 + Selective B）** 作为官方核心模型。似然层直接以总 reads 深度 $n_i$ 建模二项抽样与异方差；先验层采用分段选择性经验贝叶斯（充分锚点批次紧约束、稀疏批次 EB 收缩、零锚点批次归零正则化）；推断期完全剔除批次随机截距 $u_b$，仅输出纯序列生物学效应。
     - **正式实施与产物交付**：
       - 正式训练脚本：`scripts/15_train_hierarchical_bb_nob879.py`；
       - 正式落盘模型：`results/meta_model_hier_bb_nob879_0921.joblib`（内含 10 维标准化序列权重与过离散度参数）；
       - 接口升级：`scripts/predict.py` 默认切换至加载形态二生产模型（保留对旧版 Ridge 权重向下兼容）；
       - 配套模型卡：`results/model_card_hier_bb_nob879_0921.md` 全面归档架构、超参与推理规范。
     - **核心指标突破**：
       - 独立留出测试集（20% 留出）：Spearman $\rho = \mathbf{+0.3424}$（$p = 7.89\times 10^{-7}$），彻底治愈了传统锚定方法在测试集上的过拟合倒挂崩溃（-0.5057）；
       - LOGO-CV 全折中位相关系数：$\rho = \mathbf{+0.3635}$（有效折 9/16，超越既有基线的 +0.2970）；
       - Class A（低混杂多批核心折，跨 $\ge 3$ 批）：中位相关系数突破历史极值，达到 **$\rho = \mathbf{+0.4636}$**（所有有效核心折均呈统计学显著正相关），证实算法对真实生物学序列特征的泛化能力已突破 0.40 天花板。
- **2026-09-28 全基因组 LsT2T↔LSA crosswalk 扩建（9.28 登记；v2.0 冻结后的数据治理工作，生产模型未动）**：
  1. **扩建内容**：demo 49 NLR 之外，为全基因组 45,981 个 LsT2T* 基因建立 LSA 映射（此前 seed 路径 C 只能如实标"表达证据缺失"）。新批量定位引擎 `scripts/18_crosswalk_genome_wide.py`：numpy 2-bit rolling code 对 v1.1c 全基因组**一遍线性扫描**精配全部 seq20（含反向互补），复用 16 号 `load_v11c_genes`/`resolve_lsa` 注释解析语义。产物 `results/crosswalk_lsa_t2t_genome.csv`（与 demo 金标准同构，含 tier/票占比/簇/偏移一致性列）+ `crosswalk_lsa_t2t_genome_report.md`。**终值 tier 分布：tier1 27,661（60.2%）/ tier2 簇 7,272（15.8%）/ tier3 scaffold 922（2.0%）/ tier4 诚实缺失 10,126（22.0%）；可映射 35,855（78.0%），其中 35,783 收录于 5 组织表达矩阵取得真实 TPM**。
  2. **工程事故记录（引以为戒）**：命中数随模式集线性膨胀（demo 6.2M -> Chr01 试点 28.7M），逐 guide 扇出展开达 **660M 行触发 OOM**（4.92GiB 分配失败，试点进程阵亡）。修复双管齐下：①扫描时按 code 全局限流 20 条命中（顺序前缀保留，确定性）；②投票改 **code 级最优命中**一次选择后传播 guide 行（同 code 的 guide 命中集相同、最优命中相同），杜绝 命中×guide 双重扇出。
  3. **tier 语义扩展**：新增 `cluster_coverage`（主映射 + ≥10% 票簇成员合计占比）；弱票作废判据由"主映射票占比 <50%"改为"簇覆盖 <50%"，修复串联簇票分裂被误杀的缺陷（`mapped_cluster` 语义回归）。tier1 仍要求票占比 ≥50% + 共线偏移一致性 ≥60%；不可映射仍如实标注、**不编造映射**。
  4. **49 基因金标准回归**（`_xwalk_regress49_report.md`）：gold 可映射 35 基因**零误杀**（tier 混淆矩阵 gold 1-3 行无 tier4）；双方可映射 35 例中 lsa_primary 完全一致 31、同位点（含串联簇成员互换）32；映射状态一致 42/49。11 例分歧全部留档 `_xwalk_regress49_regress_diff.csv`：3 例定位级分歧（tandem NLR 簇固有歧义，gold 侧证据亦薄）、4 例 gold 弱解析（解析占比 5-8%）被强证据救回、4 例边缘 mapped_cluster（票占比 0.26-0.43，与救回组特征区间完全重叠、无阈值可干净分离），一并交生物学复核。
  5. **seed 接线**：`backend/app/db/seed.py` 新增 `build_expression_record`（crosswalk × 5 组织表达矩阵 join，demo 路径与路径 C 共用、消除双份逻辑）；路径 C 表达证据由占位改为真实 TPM/tau/tier，tier4 保持如实缺失文案。4 个单测覆盖（含 tier4 禁止编造 TPM 断言），真实 crosswalk 回放验证 35 映射/14 缺失与金标准一致。
  6. **配套**：`.dockerignore` 白名单放行 `crosswalk_lsa_t2t_genome.csv`（Docker 交付灌库依赖）；两份 CONTEXT.md 术语表补全基因组 crosswalk 条目；USER_MANUAL 新增 FAQ Q4（表达证据缺失横幅语义）；`test_pipeline_engine.test_genome_crosswalk` 资产完整性测试（行数=基因目录、tier4 无编造映射、`in_expression_matrix` 与表达矩阵一致）。生产模型 `meta_model_hier_bb_nob879_0921.joblib` 与效率打分链路未动。

