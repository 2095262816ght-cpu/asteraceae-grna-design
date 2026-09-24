# LSA↔T2T crosswalk 审计（0923）

> 生成脚本：`scripts/16_prep_expression_features.py`
> 样本：49 个 demo NLR 基因（`demo/app_data.csv` 的 LsaT2T* 命名空间）

## 一、覆盖率

- 可映射且在表达矩阵中：**35/49（71.4%）**
- 不可映射：14 个（见第三节）
- 分层使用分布：{1: 11, 2: 21, 3: 3, 4: 14}

## 二、映射主表

| 基因 | 染色体 | tier | LSA 主映射 | 投票占比 | 解析占比 | 簇大小 | scaffold 证据 |
|---|---|---:|---|---:|---:|---:|---|
| `LsaT2T01G023690` | Chr01 | 1 | LSA25643 | 0.82 | 0.99 | 2 | nan |
| `LsaT2T01G028320` | Chr01 | 2 | LSA25236 | 0.59 | 0.94 | 2 | nan |
| `LsaT2T01G028490` | Chr01 | 2 | LSA25230 | 1.00 | 0.64 | 1 | nan |
| `LsaT2T01G030600` | Chr01 | 4 | nan | 0.00 | 0.01 | 0 | nan |
| `LsaT2T01G031470` | Chr01 | 2 | LSA24927 | 0.79 | 0.58 | 2 | nan |
| `LsaT2T01G033120` | Chr01 | 2 | LSA24766 | 0.99 | 0.47 | 1 | nan |
| `LsaT2T01G033240` | Chr01 | 4 | nan | 0.00 | 0.04 | 0 | nan |
| `LsaT2T01G036880` | Chr01 | 3 | LSA26099 | 1.00 | 0.00 | 1 | HiC_scaffold_1:3/6 |
| `LsaT2T02G000110` | Chr02 | 2 | LSA31836 | 1.00 | 0.59 | 1 | nan |
| `LsaT2T02G002840` | Chr02 | 2 | LSA31675 | 1.00 | 0.99 | 1 | nan |
| `LsaT2T02G005790` | Chr02 | 4 | nan | 0.00 | 0.14 | 0 | nan |
| `LsaT2T02G026180` | Chr02 | 4 | nan | 0.00 | 0.08 | 0 | nan |
| `LsaT2T02G036030` | Chr02 | 2 | LSA28979 | 0.82 | 0.96 | 2 | nan |
| `LsaT2T02G039820` | Chr02 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T03G001240` | Chr03 | 2 | LSA40204 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T03G020260` | Chr03 | 2 | LSA38519 | 1.00 | 0.97 | 1 | nan |
| `LsaT2T03G035850` | Chr03 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T03G041640` | Chr03 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T04G000980` | Chr04 | 3 | LSA112 | 1.00 | 0.00 | 1 | HiC_scaffold_15:6/6 |
| `LsaT2T04G008980` | Chr04 | 1 | LSA23039 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T04G051220` | Chr04 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T04G051410` | Chr04 | 1 | LSA19262 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T04G058080` | Chr04 | 2 | LSA18757 | 0.99 | 0.32 | 1 | nan |
| `LsaT2T05G000020` | Chr05 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T05G002130` | Chr05 | 2 | LSA9322 | 1.00 | 0.96 | 1 | nan |
| `LsaT2T05G038370` | Chr05 | 1 | LSA5979 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T05G042850` | Chr05 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T05G056480` | Chr05 | 1 | LSA4360 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T06G019420` | Chr06 | 2 | LSA15294 | 0.72 | 0.21 | 2 | nan |
| `LsaT2T06G036100` | Chr06 | 1 | LSA17939 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T07G016770` | Chr07 | 2 | LSA1843 | 0.99 | 0.87 | 1 | nan |
| `LsaT2T07G017200` | Chr07 | 2 | LSA1877 | 1.00 | 0.54 | 1 | nan |
| `LsaT2T07G032940` | Chr07 | 1 | LSA3107 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T08G012370` | Chr08 | 2 | LSA10555 | 0.99 | 0.93 | 1 | nan |
| `LsaT2T08G014880` | Chr08 | 2 | LSA10767 | 1.00 | 0.98 | 1 | nan |
| `LsaT2T08G016940` | Chr08 | 1 | LSA11061 | 0.98 | 1.00 | 1 | nan |
| `LsaT2T08G017350` | Chr08 | 2 | LSA11009 | 0.96 | 0.76 | 1 | nan |
| `LsaT2T08G017810` | Chr08 | 4 | nan | 0.00 | 0.05 | 0 | nan |
| `LsaT2T08G017850` | Chr08 | 2 | LSA11017 | 0.76 | 0.97 | 2 | nan |
| `LsaT2T08G018470` | Chr08 | 4 | nan | 0.00 | 0.05 | 0 | nan |
| `LsaT2T08G021300` | Chr08 | 2 | LSA9544 | 0.44 | 0.45 | 2 | nan |
| `LsaT2T08G043380` | Chr08 | 4 | nan | 0.00 | 0.00 | 0 | nan |
| `LsaT2T08G049670` | Chr08 | 4 | nan | 0.00 | 0.06 | 0 | nan |
| `LsaT2T09G000530` | Chr09 | 1 | LSA31961 | 1.00 | 0.96 | 1 | nan |
| `LsaT2T09G001310` | Chr09 | 1 | LSA32028 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T09G006480` | Chr09 | 3 | LSA32527 | 0.89 | 0.12 | 2 | HiC_scaffold_5:6/6 |
| `LsaT2T09G024570` | Chr09 | 1 | LSA34131 | 1.00 | 1.00 | 1 | nan |
| `LsaT2T09G034910` | Chr09 | 2 | LSA34881 | 1.00 | 0.98 | 1 | nan |
| `LsaT2T09G034950` | Chr09 | 2 | LSA34950 | 0.99 | 0.43 | 1 | nan |

## 三、不可映射清单与原因分类

- `LsaT2T01G030600`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.01，scaffold 排查 nan。原因类别见下注。
- `LsaT2T01G033240`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.04，scaffold 排查 nan。原因类别见下注。
- `LsaT2T02G005790`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.14，scaffold 排查 nan。原因类别见下注。
- `LsaT2T02G026180`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.08，scaffold 排查 nan。原因类别见下注。
- `LsaT2T02G039820`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T03G035850`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T03G041640`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T04G051220`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T05G000020`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T05G042850`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T08G017810`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.05，scaffold 排查 nan。原因类别见下注。
- `LsaT2T08G018470`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.05，scaffold 排查 nan。原因类别见下注。
- `LsaT2T08G043380`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.00，scaffold 排查 nan。原因类别见下注。
- `LsaT2T08G049670`：弱票已作废（解析占比 < 0.2 且 scaffold 无共识）；解析占比 0.06，scaffold 排查 nan。原因类别见下注。

原因类别（0923 对比实验实测）：
1. **序列缺失/高度分歧**：本染色体与 scaffold 均无精配命中（如 `LsaT2T01G030600`）；
2. **v1.1c 注释缺口**：序列共线命中但最近基因模型 > 2kb（如 `LsaT2T05G000020`）；
3. **scaffold 搬迁**：可由 tier3 救回（如 `LsaT2T04G000980` → `HiC_scaffold_15`/LSA112）。

## 四、口径与方法说明

- 解析区间为启动子感知：`[start-2000, end]`（+ 链）/ `[start, end+2000]`（− 链），与 `scripts/07` 的扫描设计（TSS 上游 2000bp + 全部外显子）一致；nearest 仅在 2kb 内；
- 串联重复簇（NLR）记录 `lsa_cluster` 全部成员（投票 ≥10%），**不假设 1:1**；
- tier1 窗口依赖锚点投票 offset；tier2/3 均有封顶，最坏代价有界；
- 失败是可检测的：两类不可映射基因在 tier1/tier2 同时退化，不会被硬凑成错误答案。