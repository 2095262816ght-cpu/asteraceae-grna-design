# 文件索引（cs_pipeline/docs）

> git 仅收录代码与 Markdown 文档；PDF / docx / xlsx 被 .gitignore 忽略，本地副本保留于 paper/、survey/、notification/，团队网盘为权威源。
> 2026-09-13 重构：全目录英文命名、按类型重新分类，新旧名对照见文末表格。

本目录为"菊科菊苣族 gRNA 设计工具"项目资料库，围绕第一届全球大学生生命科学挑战赛（赛道二：AI 基因编辑与核酸工具设计）整理。

## 目录

| 目录 | 内容 |
|---|---|
| plans/ | 现行方案与分工详案（主方案最高依据） |
| reports/ | 各阶段工作报告与专项排查报告 |
| knowledge/ | 技术笔记与核心文献解读 |
| paper/ | 文献 PDF 原文与中文翻译（不入 git） |
| survey/ | 前期工具调研对比表（不入 git） |
| notification/ | 赛事官方通知（不入 git） |
| _archive/ | 已被取代的旧方案存档，**勿再引用** |
| project_progress_report.md | 项目进展全景审计报告（本目录根） |
| multiomics_implementation_plan.md | 多组学转录表达数据六大应用方案实施计划与流水线全景规范（本目录根） |
| ../ | 上级即 cs_pipeline 流水线：scripts（00–09 脚本）、data（数据）、results（结果产出）、env（环境）、app（demo）、tools（外部工具） |

## 现行方案与分工（plans/，以这批为准）

| 文件 | 说明 |
|---|---|
| plans/project_plan_v3_condensed_0907.md | **主方案**（最高依据）：公开预训练模型 + 自有橡胶草 Hi-TOM 数据 Stacking 集成，莴苣 T2T 基因组做演示对象；与详案冲突时以本文件为准 |
| plans/division_plan_master.md | 全员甘特总表、接口 F1–F7 规范、风险表、提交前检查清单（生D 维护） |
| plans/division_plan_biology.md | 生A–生D 逐人逐日详案，含 F1 数据表 12 列权威定义 |
| plans/division_plan_cs.md | 计A/计B 详案：cs_pipeline/ 目录结构、打分→Stacking→扫描→脱靶→demo 全流程脚本骨架与验收标准 |

## 工作报告（reports/）

| 文件 | 说明 |
|---|---|
| reports/env_setup_toolchain_report_0908.md | 环境搭建与工具链报告 |
| reports/A0_work_report_0909.md | A0 任务报告：数据清洗合并、双模型打分链路打通 |
| reports/B2_work_report_0922_0923.md | B2 任务验收报告：13,867,270 候选、10/10 抽样核对通过 |
| reports/B4_work_report_0925.md / B4_work_report_0926.md | demo 两日工作报告 |
| reports/demo_user_guide_0925.md | demo 使用说明 |
| reports/anonymization_checklist_1003.md | 10.3 匿名化专项检查清单（零命中） |
| reports/NLR_ID_mapping_report_0908.md | NLR ID 映射排查报告（0908 最终版） |
| reports/sequencing_data_QA_report_0913.md | 测序数据问题排查与修复报告（0913，含向老师反馈的问题清单） |

## 参考笔记（knowledge/）

| 文件 | 说明 |
|---|---|
| knowledge/project_tech_notes.md | 面向计算机背景读者的技术笔记：生物学概念（CRISPR、PAM、Hi-TOM、批次效应等）+ 数据与迁移学习的工程决策 |
| knowledge/CRISPR_core_papers_notes.md | Chen2022 与 Kim2019 两篇核心论文的中文详细解读，含算法排名数据、集成模型构建细节 |

## 赛事与调研材料

| 文件 | 说明 |
|---|---|
| notification/LSC_round1_notice.pdf | 赛事官方通知：赛程、赛道、报名与提交要求、匿名化规定（合规核对唯一依据） |
| survey/CRISPR_tools_general_comparison.docx | 前期调研：通用工具对比（报告"工具空白"背景素材） |
| survey/CRISPR_tools_plant_specific.docx | 前期调研：植物专用工具对比（同上） |

## cs_pipeline 里程碑记录

| 产物 | 位置 | 说明 |
|---|---|---|
| 07_scan_lettuce.py | ../scripts/ | gRNA 扫描完整实现：启动子 2kb + 外显子，NGG/CCN 双链 |
| scan_stats.md | ../results/ | 扫描统计（全量候选 CSV 1.6GB 存网盘） |
| app/app.py + score_deepspcas9_cli.py | ../app/ | Streamlit demo 两页版（按基因检索 / 自定义序列打分） |
| offtarget_runlog_0924.md + offtarget_counts_0924.csv | ../results/ | Cas-OFFinder v2.4.1 脱靶：19,839 guide、6,088,827 命中、mis3 中位 16 |
| scan_stats_0923.md / CHANGELOG_0927.md | ../results/ | 9.27 指标冻结记录（计A 三项待补，详见 CHANGELOG） |
| 09_aggregate_offtarget.py / run_mini_batches.ps1 | ../scripts/ | 脱靶汇总与 GPU 分批运行脚本 |
| demo_screenshots_0926/ | ../results/ | demo 三基因端到端演示截图 7 张 |
| README.md / requirements.txt | ../（cs_pipeline 根） | 10.2 打包重写（干净环境已验证可装可启动） |

## 数据文件位置说明

数据文件统一存放于 `../data/`，不在 docs/ 下：

- Hi-TOM 处理主线（hitom_clean_v1.csv 等）：`../data/hitom/`
- demo 源数据：`../data/demo/`
- 原始测序交付归档（R0/R1 测序、PCR 检测、汇总表）：`../data/raw/hitom/`
- 合并源表（原文件/结果 对）：`../data/raw/consolidation_sources/`
- 参考基因组三套：`../data/reference_genomes/`

## 9.13 重构：新旧名对照表

### docs/（本目录）

| 原名 | 新名 |
|---|---|
| ImplementationScheme/项目执行方案_v3压缩版_0907.md | plans/project_plan_v3_condensed_0907.md |
| ImplementationScheme/分工详案_总控.md | plans/division_plan_master.md |
| ImplementationScheme/分工详案_生物系.md | plans/division_plan_biology.md |
| ImplementationScheme/分工详案_计算机系.md | plans/division_plan_cs.md |
| A0_工作报告_0909.md | reports/A0_work_report_0909.md |
| B2_工作报告_0922_0923.md | reports/B2_work_report_0922_0923.md |
| B4_工作报告_0925.md / B4_工作报告_0926.md | reports/B4_work_report_0925.md / B4_work_report_0926.md |
| 环境搭建与工具链报告_0908.md | reports/env_setup_toolchain_report_0908.md |
| demo_使用说明_0925.md | reports/demo_user_guide_0925.md |
| 匿名化检查清单_1003.md | reports/anonymization_checklist_1003.md |
| report/NLR_ID映射排查报告_0908最终.md | reports/NLR_ID_mapping_report_0908.md |
| report/测序数据问题排查与修复报告_0913.md | reports/sequencing_data_QA_report_0913.md |
| knowledge/两篇CRISPR文献详细解读.md | knowledge/CRISPR_core_papers_notes.md |
| knowledge/项目技术要点笔记.md | knowledge/project_tech_notes.md |
| paper/Liu2019_HiTOM高通量突变检测.md | paper/Liu2019_HiTOM_mutation_detection_notes.md |
| paper/ 各 PDF（如 Wang2024_莴苣T2T完整基因组_PlantCommunications.pdf） | paper/ 英文名（如 Wang2024_lettuce_T2T_genome_PlantCommunications.pdf） |
| notification/第一届全球大学生生命科学挑战赛_第一轮通知.pdf | notification/LSC_round1_notice.pdf |
| data/ 两份工具对比表 docx | survey/CRISPR_tools_general_comparison.docx、survey/CRISPR_tools_plant_specific.docx |
| data/2022.01.30测序整理(1).xlsx | ../data/raw/consolidation_sources/sequencing_summary_20220130_working.xlsx |
| _archive/回复老师_莴苣多组学数据情况反馈.md | _archive/reply_teacher_lettuce_multiomics.md |
| _archive/新方案可行性报告.md | _archive/new_plan_feasibility_report.md |
| _archive/老师发的新方案.md | _archive/teacher_new_plan.md |
| _archive/迁移学习项目执行大纲.md | _archive/transfer_learning_outline.md |
| _archive/项目执行计划_融合版v2_0907.md | _archive/project_plan_merged_v2_0907.md |

### data/（../data/）

| 原名 | 新名 |
|---|---|
| 数据/Hi-Tom数据/ | raw/hitom/ |
| 数据/Hi-Tom数据/基因编辑（R0代）-Hi-Tom测序结果/ | raw/hitom/R0_sequencing/ |
| 数据/Hi-Tom数据/基因编辑（R0代）PCR检测/ | raw/hitom/R0_pcr_screening/ |
| 数据/Hi-Tom数据/基因编辑（R1代）Hi-Tom测序结果/ | raw/hitom/R1_sequencing/ |
| 数据/筛查工具/ | raw/screening_tools/（TKS_cds.fasta、notepad_urls.docx） |
| 数据/需整理文件及结果/ | raw/consolidation_sources/（×(原文件)→_original、(结果)→_processed） |
| 生菜_靶点定位_参考基因组及注释文件/ | reference_genomes/（内部 1-1/1-2/2-1/3-1 等文件名不变） |
| hitom_clean_v1.csv 等 4 个 csv（data 根） | hitom/（00–03 脚本输入输出） |
| demo_nlr50_candidates.csv / demo_nlr50_genes.txt（data 根） | demo/ |
| casoffinder_input.txt / casoff_batch_*.txt | lettuce/（08 脚本读取） |

> 附：重构时删除了 1,489 个经 MD5 校验完全相同的微信传输重复文件（文件名含 `-<12位哈希>` 后缀）与 2 份与交付副本完全相同的 (原文件) 副本，内容零丢失。
