# 计A 组 9.9 日工作报告（A0：建环境、跑通示例打分、seq30 表）—— 最终版 v3

> 执行时间：2026-09-10 晚 – 2026-09-11 午 · 对应《分工详案_计算机系》（docs/plans/division_plan_cs.md）A0 节
> 项目目录：`<项目根>\cs_pipeline\`
> v3 更新（9.11 14:48 起）：**CRISPRon 已跑通**（Windows 原生路线），9.9 任务全部完成 ✅

---

## 一、结论速览

| 9.9 任务 | 状态 | 说明 |
|---|---|---|
| ① 项目目录 + git 仓库初始化 | ✅ 完成 | commits `292f2aa` → `5350b6f`，匿名身份 team/team@example.com |
| ② conda 环境 `crispr`（py3.10 + R4.3 + 全套包） | ✅ 完成 | 从零重建成功 |
| ③ DeepSpCas9 示例序列打分 | ✅ 完成 | genet（crispr 环境）：示例序列 **71.249** |
| ④ CRISPRon 示例序列打分 | ✅ **完成（v3）** | crispron-win 环境（Windows 原生）：示例序列 **59.61**，官方测试 341 条逐字节一致 |
| ⑤ `env/environment.yml` | ✅ 完成 | 权威定义 + 实测导出 `environment_export_0909.yml` |
| ⑥ `data/hitom/hitom_seq30_0909.csv` | ✅ 完成 | 生物系数据已交付，CDS 映射生成 260 行，断言全过 |

**A0 验收标准（详案 #1、#2）全部达成**：示例序列能打出**两个模型**的分（DeepSpCas9 71.249 / CRISPRon 59.61）；hitom_seq30_0909.csv 行数=有效交付行数、seq30 全部通过一致性断言。

---

## 二、CRISPRon 攻坚过程（v3 核心内容）

原计划 CRISPRon 走 WSL Ubuntu，但本机 WSL"虚拟机平台"组件未启用（需重启生效），等不起 → 改攻 **Windows 原生路线并成功**：

1. **环境 `crispron-win`**：python 3.10 + tensorflow-intel 2.10.1（262MB wheel 走 Clash 代理从 PyPI 断点续传下载 + sha256 校验）+ biopython/pandas/numpy<2/scikit-learn；
2. **CRISPRoff 组件组装**：`CRISPRspec_CRISPRoff_pipeline.py` → `tools/CRISPRon/bin/`，`energy_dics.pkl` → `data/model/`；
3. **RNAfold 替代方案**：ViennaRNA 官方无 Windows 命令行二进制（GitHub releases 无 win 包、NSIS 安装器无法静默解压/安装、bioconda 无 win-64）→ 用 pip 官方包 `viennarna==2.7.2`（含完整 ViennaRNA 2.7.2 库）+ 自制 CLI shim（`tools/win-shims/rnafold/`）。**等价性证据：shim 产出的 341 条 spacer_self_fold 与参考输出逐字节一致**；
4. **TF 2.10 加载 TF 2.14 SavedModel：成功**（全部 fold 正常推理）——此前最大的兼容性赌注成立；
5. **官方内置测试 `test.sh`：TEST ok**——341 条测试序列的 `crispron.csv`、`CRISPRparams.tsv` 与参考输出**逐字节 diff 为空**（诚实备注：受 Bash 300s 上限，CRISPRspec 步骤分 4 片跑完再合并，数值已验证一致）；
6. **示例序列打分**：`ATCGGCTAAGCTAGGCTAGCATCGTGGATC` → **CRISPRon = 59.61**（CRISPRoff 能量分 22.21），产出留痕 `env/crispron_win_example_out/crispron.csv`。

详细记录：`env/crispron_win_native_0909.md`。commit `5350b6f`。

> 备注：原 WSL 路线材料（Ubuntu 安装 staged、CRISPRoff 预下载、续跑指南 `env/crispron_wsl_restore_0909.md`）仍保留；原生路线已通，**WSL 不再是阻塞项**——9.11 CRISPRon 批量打分可直接用 crispron-win 环境。若日后需要 ViennaRNA 完整 CLI 功能，再重启启用 WSL 或交互式安装官方安装器。

---

## 三、数据收尾（v2 内容，9.11 13:30–14:00）

### 3.1 生物系交付盘点
- 3 份 CSV（USR-4411 批 109 行、USR-8145 批 225 行、USR-5713 批 86 行，GBK 编码，列结构符合接口约定）+ 橡胶草 CDS fasta（36,239 条）；
- **start/end 坐标全部"暂不填"** → 坐标路线不可走，改 CDS 映射路线（抽样验证后实施）。

### 3.2 产出
- `data/hitom/hitom_clean_v1.csv`（**307 行**，`scripts/00_consolidate_hitom.py`）：剔除 113 行整行空白；31 行空 guide_id 补全；跨批次重复 guide 用 `uid=guide_id__batch` 保证唯一；**未做生物学判断**（不删批次、不归一化）；
- `data/hitom/hitom_seq30_0909.csv`（**260 行**，`scripts/01_build_seq30_cds.py`）：seq20+PAM 在 CDS 唯一命中后取 4nt+23nt+3nt；**断言全过**（len=30、仅 ACGT、seq30[4:24]=seq20、[24:27]=PAM）；
- 未命中 **47 行**（`results/seq30_unmatched_0909.csv`，含 TKS_0042–0052 整批靶向 evm.model.LG03.2345）——需生物系核对（内含子/UTR 或 CDS 版本）；
- 方法局限已写入 `results/seq30_build_stats_0909.md`：CDS 映射下外显子交界处的侧翼碱基为拼接上下文近似。

### 3.3 环境重建与 DeepSpCas9（v1 内容，9.10 晚 – 9.11 午）
- 27 个 A 侧资产从快照增量恢复，计B 文件零覆盖；
- `crispr` 环境重建：Python 3.10.21 + R 4.3.3 + 全套科学计算包；genet 0.17.2 + TF 2.9.3；
- DeepSpCas9 示例打分 71.2494 ✅（排掉空模型目录坑，走代理重下 checkpoint）；
- git 初始化（匿名身份），大文件（2.5GB 基因组、200MB 脱靶中间产物、44MB CDS）全部 gitignore。

## 四、遗留项（均需团队动作，非 CS 单方可决）

| 遗留项 | 需要谁/什么 | 影响 |
|---|---|---|
| 47 条 CDS 未命中 guide | 生物系核对 | 不影响主线，9.12 用 260 条命中子集算 ρ |
| 批次归一化口径 | 生物系确认可合并批次 | 影响 9.12 `eff_pct` 计算，CS 不擅自决定 |
| 数据规模档 | 307 有效行 / 260 可打分行 | 达到 D1"≥300 条"边缘（307 条），供 9.12 D2 参考 |

## 五、9.10–9.11 排期衔接（现已全部具备条件）
- ✅ `02_score_deepspcas9.py`：crispr 环境 + genet 已验证，可直接跑 260 条批量打分；
- ✅ `03_score_crispron.py`：crispron-win 环境已通（Windows 原生，无需再等重启/WSL）；
- 9.12 D2：`04_spearman_D2.py` 算两模型 ρ，按分档表决策。
