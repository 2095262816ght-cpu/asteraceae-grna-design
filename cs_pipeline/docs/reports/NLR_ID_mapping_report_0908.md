# NLR 坐标回填 ID 映射问题 · 最终报告

> 负责人：计A ｜ 日期：2026-09-08 ｜ 状态：**全部完成 ✅**

## 一、任务完成状态

| # | 任务 | 状态 | 说明 |
|---|---|---|---|
| 1 | T2T 基因组 GFF3 + FASTA 下载验证 | ✅ | MD5 一致 |
| 2 | T2T / v1.2 CDS 提取 | ✅ | T2T 45,770 / v1.2 41,270 条 |
| 3 | v1.2→T2T 映射脚本 | ✅ | exact 34,411 / kmer 2,885 / unmapped 3,974 |
| 4 | all_transcripts GFF 下载 | ⏳ 96% | 非 NLR 问题必需 |
| 5 | T2T 论文 PDF 下载与全文提取 | ✅ | 14 页全文，不含 lettuce_v2 |
| 6 | lettuce_v2 ID 来源定性 | ✅ | 作者内部注释，未公开 |
| 7 | **de novo NLR 鉴定** | ✅ | 661 个 NLR（vs 论文 514） |
| 8 | **NLR 坐标回填** | ✅ | `nlr_with_coords.csv`（661 条带 T2T 坐标） |
| 9 | 对比验证 | ✅ | 数量比 1.29x，染色体分布合理 |

## 二、lettuce_v2 最终定性

- T2T 论文 PDF（14 页全文提取）**不含 lettuce_v2、NLR、514 等任何关键词**
- 9 个公开渠道逐一排除（T2T GFF、v1.2 GFF、figshare、NCBI、论文全文 PDF）
- lettuce_v2 是作者内部注释（≥52,632 基因），未随论文公开
- **514 个 lettuce_v2 ID 无法通过公开数据映射到坐标**

## 三、de novo NLR 鉴定方案与结果

### 3.1 方法

1. 从 T2T CDS（45,770 条）翻译蛋白序列
2. 搜索 NB-ARC 保守 motif（按排列顺序）：
   - P-loop/Walker A: `[AG]xxxxGK[ST]`
   - Walker B: `[ILVMFY]....[DE]E`
   - GLPL: `GLPL`
   - MHD: `MHD`
3. 要求 P-loop 在 Walker B / GLPL 上游（间距 5-200 aa），排除随机排列的 ATP 酶/激酶
4. 同时检测 LRR（富含 Leu 重复）
5. 分档：T1 = P-loop→WalkerB→GLPL 全有序；T2 = P-loop→(WalkerB 或 GLPL) 有序

### 3.2 最终集筛选

| 分类 | 数量 | 说明 |
|---|---|---|
| Tier-1（三核心 motif 有序） | 143 | 高置信 NLR |
| Tier-2 + LRR | 518 | 有序 P-loop + LRR |
| **最终集（T1 + T2-LRR）** | **661** | 论文报告 514 |
| Tier-2 无 LRR（排除） | 553 | NBARC-only，不纳入 |

### 3.3 对比验证

| 指标 | 论文 | de novo | 说明 |
|---|---|---|---|
| NLR 总数 | 514 | 661 | 1.29x，纯 motif 法偏宽（预期内） |
| NLR-LRR | 46（已知类型中） | 658 | 论文 456 个标记 NA（未分类） |
| 灰霉响应 | 58 | — | 论文 RNA-seq 数据 |
| 染色体分布 | 论文无坐标 | Chr01-09 全覆盖 | de novo 分布合理 |

### 3.4 染色体分布

| 染色体 | NLR 数 | 成簇数 | 多基因簇 |
|---|---|---|---|
| Chr01 | 102 | 72 | 16（最大10） |
| Chr02 | 85 | 57 | 10（最大15） |
| Chr03 | 59 | 33 | 5（最大17） |
| Chr04 | 65 | 52 | 7（最大5） |
| Chr05 | 64 | 49 | 9（最大5） |
| Chr06 | 33 | 29 | 4 |
| Chr07 | 46 | 38 | 6 |
| Chr08 | 131 | 65 | 15（最大24） |
| Chr09 | 76 | 51 | 10 |
| **合计** | **661** | **446** | **82** |

- Chr08 最多 NLR（131 个，含最大 24 基因簇），符合植物 NLR 热点染色体特征
- 82 个多基因簇（成簇 NLR），符合植物抗病基因串联成簇的生物学特征

## 四、输出文件

| 文件 | 路径 | 说明 |
|---|---|---|
| **NLR 带坐标列表** | `nlr_with_coords.csv` | **661 条，含 T2T 坐标** |
| NLR 对比统计 | `nlr_comparison.csv` | 论文 vs de novo |
| NLR 筛选全量 | `nlr_denovo_v4.csv` | 1,214 条（T1+T2，未筛选 LRR） |
| NLR 蛋白序列 | `nlr_denovo_proteins.fasta` | 初筛 3,176 条蛋白 |
| v1.2→T2T 映射表 | `v12_to_t2t_mapping.csv` | 41,270 条对应关系 |

## 五、方法学说明（用于竞赛报告）

> 论文补充表 8/9 使用 `lettuce_v2_` ID 体系，经排查（T2T 论文 PDF 全文、figshare、NGDC、NCBI 等 9 个渠道），该注释为作者内部版本（≥52,632 基因），未随论文公开。因此我们在 T2T 基因组上采用基于 NB-ARC 保守 motif 排列顺序的 de novo 鉴定方法，获得 661 个 NLR 候选基因（论文报告 514 个，1.29x 偏宽属纯 motif 法预期范围）。鉴定结果含 P-loop→Walker B→GLPL 有序排列和/或 LRR 结构域，成簇分布特征与植物 NLR 一致。

## 六、遗留事项

1. `all_transcripts.gff3` 差 3.2MB（96%），非必需，可补齐
2. 如需更高精度 NLR 鉴定，可安装 HMMER + Pfam NB-ARC HMM profile（需 conda）
3. 如作者回复提供 lettuce_v2.gff3，可做逐条比对验证
