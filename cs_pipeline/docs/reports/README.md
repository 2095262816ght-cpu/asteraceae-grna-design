# 阶段工作报告与专项排查报告索引（docs/reports）

> **说明**：本目录收录项目各阶段的任务验收报告、数据治理排查报告、打分规则审计与交付检查清单，按时间跨度与业务主题归类。

---

## 一、时间线与报告总览

| 日期 | 报告文件 | 类型 | 核心内容与结论 |
|---|---|---|---|
| **09-08** | [`env_setup_toolchain_report_0908.md`](env_setup_toolchain_report_0908.md) | 环境与工程 | 基础环境（Python/WSL/ViennaRNA/CUDA）搭建、工具链可用性验证。 |
| **09-08** | [`NLR_ID_mapping_report_0908.md`](NLR_ID_mapping_report_0908.md) | 数据治理 | 莴苣 NLR 抗病基因 ID 在不同参考组版本之间的映射关系排查与锁定。 |
| **09-09** | [`A0_work_report_0909.md`](A0_work_report_0909.md) | 里程碑验收 | A0 任务：完成第一批 Hi-TOM 数据清洗合并，打通 DeepSpCas9 + CRISPRon 双模型离线打分链路。 |
| **09-13** | [`sequencing_data_QA_report_0913.md`](sequencing_data_QA_report_0913.md) | 数据治理 | 测序原始表严重问题排查（前导空格、PAM 错位、切割点漂移）及向指导老师反馈清单。 |
| **09-17** | [`progress_brief_to_advisor_0917.md`](progress_brief_to_advisor_0917.md) | 汇报材料 | 阶段中期向指导教师的进展简报与核心卡点请示。 |
| **09-20** | [`bio_lead_checklist_0920.md`](bio_lead_checklist_0920.md) | 跨学科协同 | 生物系负责人核对清单：F1 表字段定义、实验批次对应与生物学有效性确认。 |
| **09-20** | [`scoring_rules_14-15_0920.md`](scoring_rules_14-15_0920.md) | 算法规则 | 14/15 版打分规则演进、tie-break 抖动排查与修复说明。 |
| **09-21** | [`scoring_rules_16_post_ruling_0921.md`](scoring_rules_16_post_ruling_0921.md) | 算法规则 | **16/16.1 终版规则**：落实老师 9.19 裁决（剔除 360 行）、确立 969 行基准训练集与评级标准。 |
| **09-22~23**| [`B2_work_report_0922_0923.md`](B2_work_report_0922_0923.md) | 里程碑验收 | B2 任务验收：全基因组 13,867,270 个 gRNA 候选位点扫描完成，10/10 抽样交叉核验 100% 通过。 |
| **09-25** | [`demo_user_guide_0925.md`](demo_user_guide_0925.md) | 交付说明 | Streamlit Web Demo 完整使用说明（双页面：基因检索 vs 自定义序列打分）。 |
| **09-25** | [`B4_work_report_0925.md`](B4_work_report_0925.md) | 里程碑验收 | B4 任务首日报告：Demo 基础框架搭建、表格分页与打分结果呈现。 |
| **09-26** | [`B4_work_report_0926.md`](B4_work_report_0926.md) | 里程碑验收 | B4 任务次日报告：三基因（NLR/CPT1/CPT2）端到端贯通与 7 张官方演示截图留痕。 |
| **10-03** | [`anonymization_checklist_1003.md`](anonymization_checklist_1003.md) | 合规审查 | 10.3 最终交付前匿名化专项检查清单（学校、作者、院系信息零命中审查）。 |

---

## 二、分类导航

### 1. 数据质量与治理（Data QA）
- [`NLR_ID_mapping_report_0908.md`](NLR_ID_mapping_report_0908.md)
- [`sequencing_data_QA_report_0913.md`](sequencing_data_QA_report_0913.md)
- （配套根目录数据专项四部曲：[`problem.md`](../problem.md)、[`problem2.md`](../problem2.md)、[`problem3.md`](../problem3.md)、[`problem3_detailed_explanation.md`](../problem3_detailed_explanation.md)）

### 2. 算法打分与规则定案（Algorithm & Scoring）
- [`scoring_rules_14-15_0920.md`](scoring_rules_14-15_0920.md)
- [`scoring_rules_16_post_ruling_0921.md`](scoring_rules_16_post_ruling_0921.md)

### 3. 工程里程碑与交付（Milestones & Delivery）
- [`A0_work_report_0909.md`](A0_work_report_0909.md)
- [`B2_work_report_0922_0923.md`](B2_work_report_0922_0923.md)
- [`B4_work_report_0925.md`](B4_work_report_0925.md)
- [`B4_work_report_0926.md`](B4_work_report_0926.md)
- [`demo_user_guide_0925.md`](demo_user_guide_0925.md)
- [`anonymization_checklist_1003.md`](anonymization_checklist_1003.md)
