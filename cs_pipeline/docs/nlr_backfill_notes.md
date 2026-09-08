# NLR 514 坐标回填说明

## 问题
- `nlr_genes_514.csv` 的 gene_id 使用 `lettuce_v2_*` 格式
- T2T 基因组注释使用 `LsaT2T*` 格式
- 两者编号体系不同（lettuce_v2 最大 52,632，LsaT2T 最大 ~40,000）
- 无法通过编号直接映射

## 解决方案
由于 lettuce_v2 注释未公开，无法建立 ID 映射，采用以下替代方案：

1. **de novo NLR 鉴定**：在 T2T 基因组上重新鉴定 NLR，获得 661 个候选（带坐标）
2. **输出替代列表**：`nlr_genes_514_with_coords.csv` 包含 661 个 T2T NLR（非原 514 的 lettuce_v2）
3. **后续建议**：如需精确对应论文 514 个 NLR，需向作者索要 lettuce_v2 注释文件

## 文件说明
- `nlr_genes_514.csv`: 原论文 NLR 列表（lettuce_v2 ID，坐标为空）
- `nlr_genes_514_with_coords.csv`: de novo NLR 列表（LsaT2T ID，带坐标）
- `nlr_with_coords.csv`: 完整 de novo NLR 结果（含 motif 信息）
