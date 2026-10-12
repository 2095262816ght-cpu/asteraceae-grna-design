# NEWdata 数据说明

> **2026-09-21 归并记录**：`cs_pipeline/NEWdata/` 目录已撤销，全部内容并入本目录（`data/raw/hitom/NEWdata_0918/`）。
> 并入前经 MD5 全量核对：`02_HiTOM结果表格/`（18 个 xls，其中 8 个与 data/raw 既有文件字节级相同，为保批次目录完整一并保留）、
> `fastq_SY12100-USR-23709(旧批次唯一原始reads)/`（138 个 fastq，data/raw 原无、唯一拷贝）、
> `_旧数据_唯一版本/`（旧批次中 5 个 data/raw 没有的 report/整理后 xls）。
> 已删除的纯冗余：`_重复备份_fastq/`（138 个，逐文件 MD5 验证与唯一 reads 拷贝相同）、旧批次 4 个与 data/raw 字节级相同的 xls。
> 原始表格数据（877 行）此前已整理入 `data/1_Hi-results-13-NEWdata-20260918.xlsx` 并合并进 1368 行主表。

> 2026-09-18 最新进展：`02_HiTOM结果表格` 下的 17 个批次（共 18 个 Hi-TOM 结果文件，877 个样本块）已全量整理成主表格式，输出至
> `data/1_Hi-results-13-NEWdata-20260918.xlsx`（877 行，guide-id TKS_0492–1368），
> 生成脚本 `scripts/dev/build_newdata_table.py`，质检脚本 `scripts/dev/validate_newtable.py`（8项质检全部通过）。

本目录存放 Hi-TOM 测序数据。**已与 `cs_pipeline/data` 做过文件名 + MD5 + 行级内容三重比对，
只保留新数据在主目录，旧批次全部移入 `_旧数据_已在data中/`。**

## 02_HiTOM结果表格/ —— 全新批次（在 data 中无任何记录）

| 文件夹 | 行数 | 靶点示例（Sort 列） |
|---|---|---|
| USR-14333-SY7249 | 87 | refsm1 |
| USR-17012-SY8787 | 44 | refHiTom5 / refHiTom3 |
| USR-22473-SY11577 | 62 | refCALB1 |
| USR-22807-SY11791 | 20 | ref22B18 / ref22B20 |
| USR-23077-SY11854 | 20 | ref22B1 / ref23B34 |
| USR-24239-SY12397 | 15 | ref23B12 / ref22B23 等 |
| USR-28266-SY14213 | 18 | ref05nB5 / ref05nB7nB8 等 |
| USR-29107-SY14569 | 47 | ref05nB7nB8 |
| USR-29540-SY14786 | 11 | ref05nB5（编号 097 起，可能是 14213 同批后续样本） |

另有一个特殊批次：

- **USR-5448-SY2676_旧批次扩充版(比data多81行)**：该批次（2021-12-24）在
  `data/raw/hitom/R0_sequencing/20211224_transgenic_seedlings/` 已有 38 行版本；
  本目录这份 119 行完整包含旧 38 行、另多 81 行，属同一批次的扩充数据。

## _旧数据_已在data中/ —— 与 data 重复的旧批次（不需再用）

- `USR-23709-SY12100-2024.6.29`（3 个 xls）— 原始 result 与
  `data/raw/consolidation_sources/..._original.xls` 字节级相同；已入主表（68 行）。
  注：其"整理后"版本有 499 行（比原始 68 行细），如需更细粒度可回看。
- `USR-25902-SY13249-2024.8.28`（4 个 xls）— 同上，已入主表（49 行）。
- `USR-26162-SY13345` — 与 `data/.../merged_T1T2_..._original.xls` 字节级相同；已入主表（6 行）。
- `USR-4411-SY2198` — 与 `data/raw/hitom/all-SY2198-USR-4411...xls` 字节级相同；已入主表（109 行）。
- **USR-4812 / USR-4813 已于 2026-09-18 移回 02_HiTOM结果表格/**：文件虽与
  `data/raw/hitom/R0_sequencing/20211121_.../` 字节级相同，但从未进过主表，按"未使用的新数据"处理。
- `fastq_SY12100-USR-23709(旧批次唯一原始reads)` — 旧批次的 69 对原始 fastq，
  **data 里没有这份原始 reads，是唯一拷贝，勿删**。
- `_重复备份_fastq` — 上一份的 MD5 验证过的完全相同副本，纯冗余，可删。

## 2026-09-18 补充：追加纳入 5 个"有数据但从未进主表"的批次（已入库）

（与 4812/4813 同类情况，详见 docs/data-governance/problem3.md 第六节，已全部复制至 `02_HiTOM结果表格/` 并整理入新表）

| 批次 | 块数 | refs | 处理方式 |
|---|---|---|---|
| USR-4811 (SY2434, 2021-11-21) | 101 | refABCM1(87) + refABCM2(14) | 与 4812/4813 同期完整入库 |
| USR-6137 (SY2989, 2022-03-02) | 10 + 70 = 80 | A: refSP1；B: refL3/L1andL2/refM/refSP3 | 两版本靶点无交集，作为复测与主交付互补入库 |
| USR-6444 (SY3120, 2022-03) | 48 | refsm1/refsp5/refsm2/refsn2(+refsp1) | 以 LYM/2 目录修订版 B 版入库 |
| USR-6883 (SY3382, 2022-04-27) | 94 | refsn2/refsm1/refsp5/refsm2 | 完整入库 |
| USR-7342 (SY3618) | 26 | refsp1/refsp2/refSP3/refsm1 | 完整入库（refsp1/refsp2 已规范化合并） |

## 比对方法（2025-09-18）

1. 全量文件名比对；2. NEWdata 全部文件 MD5 × data 全部文件（大小预筛后校验）；
3. 同名/疑似表格逐行内容比对（行集合包含/差集）。
主表依据：`data/1_Hi-results-12-20260913.xlsx` Sheet1 的 batch 列
（已含 USR-8145 / 4411 / 5713 / 23709 / 5712 / 25902 / 26162）。
