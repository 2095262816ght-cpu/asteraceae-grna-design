# B2 任务工作报告 · gRNA 扫描脚本（9.22–9.23）

> 负责人：计B ｜ 报告日期：2026-09-08 ｜ 任务状态：**已完成，验收通过 ✅**

---

## 一、任务定义（分工详案原文）

> **B2 · 9.22–9.23（周二、三）gRNA 扫描脚本**
> - 只扫描基因区：启动子（TSS 上游 2000bp，按链方向取）+ 所有外显子
> - 用 pyfaidx 随机访问取序列，不把 2.59Gb 整个读进内存
> - 候选枚举：正链找 NGG 取上游 20nt；负链找 CCN 取下游 20nt 反互补
> - 9.22：GFF 解析 + regions_of；1 条染色体小跑验证（抽 10 个候选手工核对）
> - 9.23：全基因组跑 + 统计产出写入 `scan_stats.md`
> - 9.23 晚：给生B 交来的 `nlr_genes_514.csv` 按 gene_id 回填坐标，9.24 前交回生B 抽查

**验收标准**：`grna_candidates_lettuce.csv` 产出；每基因候选数分布合理（全为 0 或全 >500 都是 bug 信号）；抽 10 条手工核对通过。

## 二、环境准备与 B1 状态确认

| 检查项 | 状态 | 说明 |
|---|---|---|
| 莴苣 T2T 基因组 fasta | ✅ | `LsT2T_genome.fa`（2,626,286,211 bp，9 条染色体） |
| GFF3 注释 | ✅ | `LsT2T_annotation.gff3`（602,936 行，45,770 基因） |
| pyfaidx | ✅ | pip 安装 0.9.0.4（替代 samtools faidx，纯 Python 可用） |
| biopython | ✅ | pip 安装 1.88（用于反向互补） |
| pandas | ✅ | 已装 |
| samtools | ⚠️ 未装 | 用 pyfaidx 替代，验收方式改为 Python 内核对 |

GFF 结构核对（分工详案要求"必须先看实际文件再写死"）：
- feature 命名：`gene` / `mRNA` / `exon` / `CDS`（不是 transcript）
- 外显子 Parent 直接指向 mRNA，mRNA Parent 指向 gene，映射链完整（236,163 个 exon 全部成功映射到基因，0 个落空）

## 三、执行过程

### 3.1 脚本实现

产物脚本：[`scripts/07_scan_lettuce.py`](../../scripts/07_scan_lettuce.py)

按分工详案骨架实现，关键点：
1. `pd.read_csv` 解析 GFF，`feature == "gene"` 提取 45,770 个基因
2. exon → mRNA → gene 两层映射
3. `Fasta(as_raw=True)` 随机访问，不整读 2.6Gb
4. 正则前瞻匹配 `(?=([ACGT]GG))` / `(?=(CC[ACGT]))`，逐基因扫描
5. 按 `chrom+start+end+strand` 去重；取 30nt 上下文（seq20+PAM+侧翼），非 `[ACGT]{30}` 的边界候选丢弃
6. 输出 `Lsat_xxxxxx` 格式的 guide_id

### 3.2 小跑验证（对应 9.22 任务）

先跑 Chr01 单染色体：
- 4,660 个基因 → 1,445,105 个候选
- 每基因平均 310.1 个，分布正常

### 3.3 全基因组扫描（对应 9.23 任务）

| 染色体 | 基因数 | 候选数 | 每基因平均 |
|---|---|---|---|
| Chr01 | 4,660 | 1,445,105 | 310.1 |
| Chr02 | 4,803 | 1,468,179 | 305.7 |
| Chr03 | 4,959 | 1,487,162 | 299.9 |
| Chr04 | 6,332 | 1,909,312 | 301.5 |
| Chr05 | 6,164 | 1,847,198 | 299.7 |
| Chr06 | 3,965 | 1,194,594 | 301.3 |
| Chr07 | 4,192 | 1,257,715 | 300.0 |
| Chr08 | 5,883 | 1,811,016 | 307.8 |
| Chr09 | 4,812 | 1,446,989 | 300.7 |
| **合计** | **45,770** | **13,867,270** | **303.0** |

- **扫描耗时：320 秒**（远低于分工详案 2 小时的告警线，无需启动降级预案）
- 去重后无重复坐标（0 条重复）
- seq30 有效性过滤后保留全部 13,867,270 条（边界截断候选为 0）

## 四、验收结果

### 4.1 每基因候选数分布 ✅

| 统计量 | 值 | 判定 |
|---|---|---|
| 平均 | 303.0 | 正常 |
| 中位数 | 260 | 正常 |
| 25%/75% 分位 | 200 / 356 | 正常 |
| 最小 / 最大 | 1 / 1,428 | 无全 0、无异常爆表 |

候选数为 0 的基因：0 个（无 bug 信号）；候选 >500 的基因存在但非全部（长基因外显子多属正常）。

### 4.2 抽样核对 ✅（10/10 通过）

随机抽 10 条，用 pyfaidx 从基因组重新取序列逐条比对：

```
PASS Lsat_5198818  LsaT2T04G028280  Chr04:139208558-139208580(+)  GGTATTATAAATCCCAATTG+TGG
PASS Lsat_8011338  LsaT2T05G056570  Chr05:349105691-349105713(+)  ATGATTAATAACATCATTTG+AGG
PASS Lsat_11688046 LsaT2T08G036670  Chr08:161765759-161765781(+)  CAGAGTTAATGGGAGAGAAG+GGG
PASS Lsat_12747254 LsaT2T09G011490  Chr09:35943185-35943207(+)   ACATTTTATATTTAAATTGA+TGG
PASS Lsat_2582511  LsaT2T02G036260  Chr02:199685372-199685394(-) TGAATGCACATCTTCACATG+GGG
PASS Lsat_11751862 LsaT2T08G038770  Chr08:178782264-178782286(-) TTATATTTTTATACATATTT+TGG
PASS Lsat_11793136 LsaT2T08G040270  Chr08:187746995-187747017(-) TTTACGAGACTTGGATACAA+AGG
PASS Lsat_12439879 LsaT2T09G000570  Chr09:2621339-2621361(-)    AGCTTCATAAAGAGATTCTT+CGG
PASS Lsat_3187245  LsaT2T03G009670  Chr03:41430673-41430695(-)  ATCAGATATTAACTAAAATA+GGG
PASS Lsat_3056907  LsaT2T03G004960  Chr03:22250283-22250305(+)  AGCGGTGGGATTAGCCGTGA+CGG
```

正链、负链各 5 条，坐标与序列全部一致。

### 4.3 理论交叉验证

- 总扫描区域：启动子 91.5Mb + 外显子 85.4Mb = **176.9Mb**（占基因组 6.7%，符合分工详案 ~6% 的设计预期）
- 理论候选（NGG/CCN 各约 1/16 随机频率）：约 2,210 万
- 实际：1,387 万（比值 0.63，莴苣基因组 AT 富集导致 NGG 频率略低，合理）

## 五、NLR 514 坐标回填（9.23 晚附带任务）

### 5.1 问题

- `nlr_genes_514.csv` 的 gene_id 为 `lettuce_v2_*` 格式（编号范围 846–52,632）
- T2T GFF 使用 `LsaT2T*` 格式
- 经前期排查（9.7–9.8 已完成），lettuce_v2 是作者未公开的内部注释，**无法通过公开数据建立 ID 映射**

### 5.2 处理

用已完成的 de novo NLR 鉴定结果（661 个带 T2T 坐标的 NLR）作为替代回填：

- 输出：`nlr_genes_514_with_coords.csv`（661 行，团队网盘 `data/lettuce_t2t/`）
- 说明文档：`nlr_backfill_notes.md`（团队网盘）
- 回填脚本：`backfill_nlr_514.py`（团队网盘 `mapping/`）

**注意**：这 661 个是 de novo 鉴定的 T2T NLR（与论文 514 个数量级吻合，1.29x），不是原 lettuce_v2 ID 的直接回填。如需精确对应，需向作者索要 lettuce_v2.gff3。此替代方案需与生B 确认是否接受。

## 六、产物清单

| 文件 | 说明 | 大小/规模 |
|---|---|---|
| `grna_candidates_lettuce.csv` | **gRNA 候选主产物** | 13,867,270 行 |
| `scan_stats.md` | 扫描统计报告 | — |
| `nlr_genes_514_with_coords.csv` | NLR 回填结果（替代方案） | 661 行 |
| `nlr_backfill_notes.md` | 回填问题说明 | — |
| `scripts/07_scan_lettuce.py` | 扫描脚本 | 备查 |
| `scripts/backfill_nlr_514.py` | 回填脚本 | 备查 |

候选 CSV 列：`guide_id, gene_id, chrom, start, end, strand, seq20, pam, region_type, seq30`

## 七、偏差与风险说明

### 7.1 候选总量超预期（重要，需团队知悉）

- 分工详案预期"几十万到一百万条"，实际 **1,387 万条**
- 原因：详案按"约 4 万基因 × 平均 4kb"估算扫描区域约 160Mb，但候选密度约 7.8 条/kb/双链（NGG+CCN 合并），比直觉估计高
- **影响与对策**（呼应分工详案 B3 节的既定策略）：
  - 下游 Cas-OFFinder 脱靶分析不能跑全量（1,387 万 × 2.6Gb 基因组不可行）
  - 按详案既定方案：先用计A 的 predict.py 给候选打分，**只取每基因 top 5**（约 22.9 万条），再按 demo 范围收敛到 20–50 个代表基因跑脱靶
  - ⚠️ 该取舍需按详案要求在群里确认，写进报告"方法与局限"

### 7.2 环境偏差

- samtools 未安装，faidx 索引由 pyfaidx 自动生成（`.fai` 等效功能），验收改为 Python 内比对，不影响功能

## 八、下一步（B3 · 9.24 衔接）

1. 等计A 的打分模型（predict.py），对 1,387 万候选批量打分
2. 按"每基因 top 5"收敛 → Cas-OFFinder 脱靶预测（9.24）
3. NLR 替代回填方案交生B 确认（是否接受 661 个 de novo NLR，或继续向作者索要 lettuce_v2 注释）
4. 中心粒区域 `centromere_regions.bed`（F3，生物系 9.23 晚交付）到位后整合进过滤流程
