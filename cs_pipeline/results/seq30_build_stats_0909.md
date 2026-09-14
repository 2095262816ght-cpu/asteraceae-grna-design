# A0 · Hi-TOM 交付合并 + seq30 构建统计（0909）

## 输入行数

| 源文件 | 行数 |
|---|---|
| all-SY2198-USR-4411-Hi-TOM-sequencing-result（副）.csv | 109 |
| all-SY4070-USR-8145-Hi-TOM-sequencing(1).csv | 225 |
| 2022.01.30测序整理(1)(6)(2)(4).csv | 86 |
| **合并后总行数** | **420** |

## 机械清洗剔除 / 补全

| 类别 | 计数 | 说明 |
|---|---|---|
| seq20 非 [ACGT]{20} 或 pam 非 NGG 剔除 | 113 | 全部来自 SY4070 文件，均为**整行空白**行（14 列全 NA），非有效数据 |
| guide_id 为空补 TKSAUTO | 31 | 均有完整 seq20/pam/gene_id，按 `TKSAUTO_{batch}_{四位序号}` 补全 |
| uid（guide_id__batch）重复 | 0 | 同批同 guide 无重复行 |
| guide_id 跨批次/多 rep 重复 | 9（去重后 298 个 guide） | 同一 guide 多批次测定，属正常，保留 |

**`data/hitom/hitom_clean_v1.csv`：307 行**

## CDS 映射构建 seq30

| 类别 | 计数 |
|---|---|
| 成功映射（ok） | 260 |
| gene_id 不在 CDS（no_gene） | 0 |
| 未命中（no_hit） | 47 |
| 多重命中（multi_hit） | 0 |
| 侧翼不足（boundary） | 0 |

**`data/hitom/hitom_seq30_0909.csv`：260 行**；未匹配清单：`results/seq30_unmatched_0909.csv`（47 行）。

硬断言全部通过：`len(seq30)==30`、fullmatch `[ACGT]{30}`、`seq30[4:24]==seq20`、`seq30[24:27]==pam`。

未命中行按批次分布：USR-8145 31、USR-4411 11、USR-4424/4445/4453/4455/8146 各 1。
典型例：USR-4411 批次 TKS_0042–TKS_0052 靶向 `evm.model.LG03.2345` 的
`TTATTTTTCATGTTCTAATT + TGG`，在该基因 CDS 正反链均无命中——可能该 guide
位于内含子/UTR/基因间区，或交付序列与 CDS 版本不一致，需生物系核对。

## 最终 seq30 表 batch 分布（前 10）

```
USR-5713    86
USR-8145    80
USR-4411    54
USR-4412~4455, 8146  各 1（共 40 个批次各 1 行）
```

cds_strand 分布：+ 链 260、- 链 0（所有唯一命中均在正链）。

## 前 5 行样例

```
               uid guide_id             gene_id                seq20 pam    batch  indel_pct                          seq30 cds_strand  cds_offset
TKS_0001__USR-5713 TKS_0001 EVM.MODEL.LG05.2725 GGCGTTAGATTGACAGAAGA CGG USR-5713       5.55 ATTCGGCGTTAGATTGACAGAAGACGGTGG          +          96
TKS_0002__USR-5713 TKS_0002 EVM.MODEL.LG05.2725 GGCGTTAGATTGACAGAAGA CGG USR-5713       5.48 ATTCGGCGTTAGATTGACAGAAGACGGTGG          +          96
TKS_0003__USR-5713 TKS_0003 EVM.MODEL.LG05.2725 GGCGTTAGATTGACAGAAGA CGG USR-5713       7.24 ATTCGGCGTTAGATTGACAGAAGACGGTGG          +          96
TKS_0004__USR-5713 TKS_0004 EVM.MODEL.LG05.2725 GGCGTTAGATTGACAGAAGA CGG USR-5713       6.63 ATTCGGCGTTAGATTGACAGAAGACGGTGG          +          96
TKS_0005__USR-5713 TKS_0005 EVM.MODEL.LG05.2725 GGCGTTAGATTGACAGAAGA CGG USR-5713       6.32 ATTCGGCGTTAGATTGACAGAAGACGGTGG          +          96
```

## 方法学与局限

- 交付表无基因组坐标（start/end 均为"暂不填"），故走 CDS 映射：
  在对应 gene_id 的 CDS 序列及其反向互补中 regex 前瞻搜索 seq20+pam（23nt），
  要求正反链合计恰好 1 次命中，命中后取上游 4nt + 23nt + 下游 3nt。
- **局限**：若命中位置跨越外显子交界处，侧翼碱基是 CDS（转录本拼接）上下文，
  而非基因组上下文（基因组上侧翼可能隔内含子）。下游模型若假定基因组上下文
  需注意此点。
- 本步骤仅机械清洗，未做生物学判断（不删批次、不归一化效率）。
