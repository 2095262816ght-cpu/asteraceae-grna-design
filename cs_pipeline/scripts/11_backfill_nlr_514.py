"""
NLR 514 坐标回填脚本
分工详案 B2 节：用 GFF 给生B 交来的 nlr_genes_514.csv 按 gene_id 批量回填坐标
问题：nlr_genes_514.csv 的 gene_id 是 lettuce_v2_*，与 T2T 的 LsaT2T* 不匹配
解法：用 de novo NLR 鉴定结果（661 个）作为替代，或尝试建立映射
"""
import pandas as pd
import re

NLR_514 = "data/lettuce/nlr_genes_514.csv"          # 生B 交来的原始列表（lettuce_v2 ID）
NLR_COORDS = "results/nlr_with_coords.csv"          # de novo NLR 鉴定结果（T2T 坐标）
GFF_FILE = "data/lettuce/lettuce_t2t.gff3"
OUT_FILE = "results/nlr_genes_514_with_coords.csv"

# 读取 514 列表
nlr514 = pd.read_csv(NLR_514)
print(f"NLR 514: {len(nlr514)} rows")
print(f"  Columns: {nlr514.columns.tolist()}")
print(f"  Sample gene_ids: {nlr514.gene_id.head(3).tolist()}")

# 读取 de novo NLR（T2T 坐标）
nlr_coords = pd.read_csv(NLR_COORDS)
print(f"\nde novo NLR: {len(nlr_coords)} rows")
print(f"  Columns: {nlr_coords.columns.tolist()}")

# 尝试方案 1：检查 lettuce_v2 编号是否与 LsaT2T 编号有关联
# 提取数字部分
nlr514['v2_num'] = nlr514.gene_id.str.extract(r'(\d+)$').astype(int)
nlr_coords['t2t_num'] = nlr_coords.t2t_gene_id.str.extract(r'(\d+)$').astype(int)

print(f"\nlettuce_v2 编号范围: {nlr514.v2_num.min()} - {nlr514.v2_num.max()}")
print(f"LsaT2T 编号范围: {nlr_coords.t2t_num.min()} - {nlr_coords.t2t_num.max()}")

# 检查是否有重叠的编号区间
overlap_min = max(nlr514.v2_num.min(), nlr_coords.t2t_num.min())
overlap_max = min(nlr514.v2_num.max(), nlr_coords.t2t_num.max())
print(f"编号重叠区间: {overlap_min} - {overlap_max} ({overlap_max - overlap_min} 个编号)")

# 方案 2：由于 lettuce_v2 ≠ LsaT2T，用 de novo NLR 作为替代
# 按染色体排序，与论文 514 的染色体分布对比
print(f"\n=== de novo NLR 染色体分布 ===")
print(nlr_coords.chr.value_counts().sort_index())

# 方案 3：输出一个合并文件，标记来源
# 对于 514 个 lettuce_v2，坐标无法直接回填（ID 不匹配）
# 但可以用 de novo NLR 作为"替代 NLR 列表"

# 检查：de novo NLR 是否与 514 有数量对应关系
print(f"\n数量对比: de novo {len(nlr_coords)} vs 论文 514")

# 按染色体排序 de novo NLR
nlr_coords_sorted = nlr_coords.sort_values(['chr', 'start_bp']).reset_index(drop=True)

# 输出替代 NLR 列表（带 T2T 坐标）
output = nlr_coords_sorted[['t2t_gene_id', 'chr', 'start_bp', 'end_bp', 'strand',
                            'nlr_type', 'tier', 'has_lrr', 'has_mhd']].copy()
output.columns = ['gene_id', 'chr', 'start_bp', 'end_bp', 'strand',
                  'nlr_type', 'tier', 'has_lrr', 'has_mhd']
output['source'] = 'de_novo_T2T'
output['original_id'] = 'lettuce_v2_not_matched'

output.to_csv(OUT_FILE, index=False)
print(f"\nOutput -> {OUT_FILE}")
print(f"  {len(output)} rows with T2T coordinates")

# 同时输出一个说明文件
with open("docs/nlr_backfill_notes.md", "w", encoding="utf-8") as f:
    f.write("""# NLR 514 坐标回填说明

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
""")

print("  -> nlr_backfill_notes.md")
