# Cas-OFFinder 脱靶预测运行日志（B3 · 9.24）

> 冻结日期：9.27 ｜ 本日志由实际运行产物（输入文件、控制台日志、原始输出）复核重建，所有数字均可由下列文件复核。

## 工具与版本

- Cas-OFFinder **v2.4.1**（2021-01-23 构建），Windows 64 位二进制：`tools/cas-offinder/cas-offinder.exe`
- 官方下载地址：https://github.com/snugel/cas-offinder （Releases 页 win64 包）
- 运行设备：GPU（日志显示 `Total 2 device(s) found`，批处理脚本以 `G0` 调用）

## 范围决策（按详案 B3「性能现实检查」执行）

- 全量候选 13,867,270 条 × 2.6 Gb 基因组在常规硬件上不可行；
- 按详案既定策略收敛到 demo 演示范围：**49 个 NLR 代表基因的全部候选，共 19,839 条 guide**（`data/demo/demo_nlr50_candidates.csv`）；
- 全量扫描框架保留（`scripts/07_scan_lettuce.py` + `scripts/08_casoffinder_run.sh`），报告「方法与局限」中注明。

## 输入

- 模式：`NNNNNNNNNNNNNNNNNNNNNGG`（20 N + GG），允许错配数 **3**，DNA/RNA bulge 默认 0
- 基因组：`data/lettuce/chrs/`（莴苣 T2T，9 条染色体各一个 .fa）
- 完整输入样例：`data/casoffinder_input.txt`（19,841 行 = 2 行头 + 19,839 条 guide）

## 运行命令（实际执行方式：40 个分批 + GPU）

```powershell
# scripts/run_mini_batches.ps1（PowerShell）：每批约 500 条 guide
foreach ($i in 0..39) {
  & tools\cas-offinder\cas-offinder.exe data\mini_$tag.txt G0 results\off_mini_$tag.txt
}
# 40/40 批全部成功后合并：
Get-Content results\off_mini_*.txt | Set-Content results\offtarget_raw_0924.txt
```

等价单批命令（CPU 复现用，见 `scripts/08_casoffinder_run.sh`）：

```bash
tools/cas-offinder.exe data/lettuce/casoffinder_input.txt C results/offtarget_raw_0924.txt
```

## 产出与规模数字（冻结）

| 项 | 数值 | 复核来源 |
|---|---|---|
| 输入 guide 数 | 19,839（49 个基因） | `data/casoffinder_input.txt` / 40 个 mini 批合计 |
| 原始命中位点总数 | **6,088,827** | `results/offtarget_raw_0924.txt` 行数 |
| 控制台日志 | — | `results/casoffinder_console.log` |
| 汇总表 | `results/offtarget_counts_0924.csv` | `scripts/09_aggregate_offtarget.py` 生成 |

## 汇总口径（scripts/09_aggregate_offtarget.py）

- `exact_match_count`：错配数 = 0 的位点数（基因组内完全匹配）；自检：19,839 条 guide 全部 ≥1 ✅
- `offtarget_count_misN`：1 ≤ 错配数 ≤ N 的脱靶位点数（不含完全匹配本身）
- 相同 seq20 的 guide（285 条重复）脱靶谱必然相同（输入模式为 seq20+NNN），按 seq20 多对一映射

## 汇总结果（冻结数字）

| 指标 | 数值 |
|---|---|
| guide 总数 | 19,839 |
| 脱靶 mis3 = 0（无 ≤3 错配脱靶）的 guide | 782 |
| 脱靶 mis3 中位数 / 均值 / 最大值 | 16 / 326.7 / 132,951 |

汇总表已并入 demo 数据（`demo/app_data.csv`，经 `demo/prepare_demo_data.py` 重建）。
