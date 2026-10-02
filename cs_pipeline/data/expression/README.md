# 表达矩阵数据目录（data/expression）

本目录存放项目引入的转录组（RNA-seq）基因表达量矩阵数据，用于多组学特征工程、组织特异性敲除靶点推荐及 Web 系统展示。
数据于 2026-09-22 接收，由原 `newdata/` 规范化迁移至本目录。

---

## 一、文件清单与数据规范

| 文件名 | 物种 | 基因数量 | 数据维度 | 数据口径与说明 |
|---|---|---|---|---|
| `1-3_lettuce_5tissue_expression_matrix.csv` | 莴苣（茎用莴苣） | 40,267 | 5 组织（根、茎、叶、花、种子） | **均值表达表**（FPKM/TPM），已对各生物学重复取均值。基因 ID（`LSA1`~`LSA40268`）与 `data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff` 严格对齐。 |
| `lettuce_biorep_expression_matrix.csv` | 莴苣（茎用莴苣） | 40,267 | 16 个测序文库（含生物学重复） | **原始生物学重复表**，涵盖 Root (2 rep), Stem (5 rep), Leaf (7 rep), Flower (1 rep), Seed (1 rep)。供方差检验与差异表达分析使用。 |
| `2-3_TKS_Tiss-Dev-Expression(1).xlsx` | 橡胶草（TKS） | 36,239 | S1–S9 发育期 × 5 大组织（共 80 样本） | **全发育期高分辨率表达谱**。覆盖根（gen, S1–S9）、叶（ye, S1–S9）、胶乳（jiaoru, S4–S9）、花（hua, S6）、花葶（huating, S6），均含 3 次生物学重复。基因 ID（`evm.model...`）与 `data/reference_genomes/2-2_TKS.genome.gff3` 严格对齐。 |
| `supportingpaper.md` | 说明便签 | — | — | 原始说明文档，记录了样本缩写对照与处理指引。 |

---

## 二、与原参考基因组体系的对应关系

本项目的数据编号遵循统一规范：
- `1-x` 系列（茎用莴苣）：
  - `data/reference_genomes/1-1_Stem_lettuce_v1.1c.gff`（基因组注释）
  - `data/reference_genomes/1-2_Stem_lettuce_genome.v1.1c.fa`（基因组序列）
  - `data/reference_genomes/1-3_Stem_lettuce_ATAC_peaks.xlsx`（ATAC-seq 染色质开放区）
  - `data/expression/1-3_lettuce_5tissue_expression_matrix.csv`（转录组表达矩阵）
- `2-x` 系列（橡胶草 TKS）：
  - `data/reference_genomes/2-1_TKS.genome.fasta`（基因组序列）
  - `data/reference_genomes/2-2_TKS.genome.gff3`（基因组注释）
  - `data/expression/2-3_TKS_Tiss-Dev-Expression(1).xlsx`（转录组全发育期表达矩阵）

---

## 三、靶基因匹配验证事实

经 `Get-FileHash` 与 Python 脚本交叉比对：
1. 原 Hi-TOM 实测训练集涉及的 11 个橡胶草靶基因（如 `EVM.MODEL.LG05.2725`、`EVM.MODEL.LG01.555` 等）在 `2-3_TKS_Tiss-Dev-Expression(1).xlsx` 中 **100% 存在（11/11 命中）**；
2. 莴苣 40,267 个基因完整覆盖茎用莴苣全外显子空间。
