# 全基因组 LSA↔T2T crosswalk 审计报告

> 生成脚本：`scripts/18_crosswalk_genome_wide.py`（批量定位引擎）
> guides 来源：`lettuce_all_genes_top100_candidates.csv`
> 基因数：49，guide 解析占比均值：75.6%

## tier 分布

| tier | 语义 | 基因数 | 占比 |
|---|---|---|---|
| 1 | mapped | 33 | 67.3% |
| 2 | mapped_cluster | 7 | 14.3% |
| 3 | mapped_scaffold | 2 | 4.1% |
| 4 | unmappable | 7 | 14.3% |

## 映射质量

- 可映射基因（tier1-3）：42（85.7%）
- 其中收录于 5 组织表达矩阵：42
- 主映射票占比均值：72.8%
- 串联簇（n_cluster>1）：17
- scaffold 搬迁（tier3）：2

## 不可映射（tier4）样例

| 基因 | 解析占比 | 票占比 | 簇覆盖 | 弱票作废 |
|---|---|---|---|---|
| `LsaT2T01G030600` | 10.0% | 67.9% | 67.9% | True |
| `LsaT2T01G033240` | 68.9% | 43.8% | 43.8% | False |
| `LsaT2T02G039820` | 42.5% | 16.5% | 16.5% | False |
| `LsaT2T03G035850` | 8.7% | 25.0% | 40.6% | True |
| `LsaT2T04G051220` | 36.4% | 11.2% | 11.2% | False |
| `LsaT2T05G000020` | 43.5% | 9.2% | 0.0% | False |
| `LsaT2T05G042850` | 39.7% | 10.4% | 10.4% | False |

## 金标准回归（49 个 demo NLR 基因）

- 双方可映射基因：35，lsa_primary 完全一致：31（88.6%），同位点一致（含串联簇内成员互换）：32（91.4%）
- 映射状态（可映射/不可映射）一致：42/49（85.7%）
- 不一致明细：`_xwalk_regress49_regress_diff.csv`

tier 混淆矩阵（行=金标准，列=新引擎）：

```
tier_new    1  2  3  4
tier_gold             
1          11  0  0  0
2          19  2  0  0
3           0  1  2  0
4           3  4  0  7
```