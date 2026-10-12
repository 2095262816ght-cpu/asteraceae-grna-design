# 数据治理专项排查记录（docs/data-governance）

> **说明**：本目录收录 Hi-TOM 实测数据表历次系统性排查与修复的全过程记录（"问题排查四部曲"）。每处更正均有基因组序列或原始测序 reads 双重证据，改正前后均有备份可回滚。
> **注意**：多份脚本注释与历史数据备注中以 `docs/problem.md` 等旧路径引用本系列文档，2026-10-10 起统一存放于 `docs/data-governance/`，文件名保持不变。

---

## 文档索引

| 文件 | 编号 | 核心内容 |
|---|---|---|
| [`problem.md`](problem.md) | 数据治理① | `1_Hi-results-12-20260913.xlsx` 491 行原始数据全面质检：首尾空格清理、批次笔误更正、二倍体真实离散表型确认。 |
| [`problem2.md`](problem2.md) | 数据治理② | 221 行链向与 PAM（CCA→ACT）自洽修复、5712 批 61 行右侧口径写回、487 行全量重跑记录与同源拷贝（LG01.6995/6999）分析。 |
| [`problem3.md`](problem3.md) | 数据治理③ | NEWdata 877 行新批次整理：事故块识别、批次效应锚定校正、未确认 guide 隔离与 17 批次分类处置。 |
| [`problem3_detailed_explanation.md`](problem3_detailed_explanation.md) | 数据治理④ | NEWdata 质检深度生物学解读：面向非生物背景成员讲解 Hi-TOM 测序原理、野生型/突变型读段比例失真的生化原因。 |

---

## 与其他文档的关系

- 全过程统揽见 [`../reports/project_progress_report.md`](../reports/project_progress_report.md)（含 9.14–9.16 数据更正、9.18 扩表并入时间线）。
- 由此确立的训练基准口径（969 行基准集）见 [`../reports/scoring_rules_16_post_ruling_0921.md`](../reports/scoring_rules_16_post_ruling_0921.md)。
