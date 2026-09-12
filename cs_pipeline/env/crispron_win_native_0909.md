# A0 · CRISPRon Windows 原生跑通记录（0909）

**结论：路线成功。** CRISPRon 在 Windows 原生（Git Bash + conda，无 WSL）完整跑通，
内置测试 `TEST ok`（全部输出文件与 `test/outdir.original` 逐字节一致），
示例 30bp 序列打出 CRISPRon 分数 **59.61**。

## 逐步结果

| 步骤 | 结果 | 说明 |
|---|---|---|
| 1. conda env `crispron-win` (python 3.10) | ✅ | `conda create -n crispron-win python=3.10 -y` |
| 1. pip 依赖 | ✅ | tensorflow-intel **2.10.1**（手动 curl 断点续传 wheel，sha256 校验 OK；清华镜像 DNS 间歇失败，改走代理从 PyPI 下载）、biopython 1.88、pandas 2.3.3、numpy 1.26.4、scikit-learn 1.7.2、matplotlib 3.10.9、viennarna 2.7.2 |
| 2. CRISPRoff 组件组装 | ✅ | `CRISPRspec_CRISPRoff_pipeline.py` → `tools/CRISPRon/bin/`；`energy_dics.pkl` → `tools/CRISPRon/data/model/`（来自 crisproff-1.1.2.tar.gz） |
| 3. RNAfold | ✅（替代方案） | 见下节 |
| 4. 内置测试 | ✅ `TEST ok` | 见下节 |
| 5. 示例序列打分 | ✅ | `ATCGGCTAAGCTAGGCTAGCATCGTGGATC` → CRISPRon = **59.61** |

## RNAfold 来源与版本（重要偏差记录）

- 官方 GitHub releases（v2.6.3–v2.7.2）**均无 Windows 二进制**；官网
  `https://www.tbi.univie.ac.at/RNA/download/win/windows/Install-ViennaRNA-2.7.2_64bit.exe`
  下载成功（77 MB），但 7za 23.01 报 `Cannot open the file as archive`
  （NSIS 3 安装包无法解出），`cmd /c "... /S /D=..."` 静默安装挂起（疑似 UAC 提权阻塞）。
- `conda install -c bioconda viennarna` 确认无 win-64 包（PackagesNotFoundError）。
- **最终方案**：pip 包 `viennarna==2.7.2`（官方 ViennaRNA Python 绑定，含 win_amd64 wheel）
  + 自制 RNAfold CLI shim（`tools/win-shims/rnafold/`，运行副本在 `tools/ViennaRNA/bin/`）：
  - `RNAfold_shim.py`：用 `RNA.fold_compound(seq).mfe()` 复刻 `RNAfold --noPS` 的 stdin/stdout 协议与 `--version`；
  - `RNAfold.bat`：供 pipeline 内 Windows `subprocess.Popen(..., shell=True)`（cmd.exe）调用；
  - `RNAfold`（bash 版）：供 `CRISPRon.sh` 的 `RNAfold --version` 检查。
- 正确性证据：pipeline 只用 RNAfold 算 20nt spacer 的 MFE（`get_rnafold_eng`）。
  shim 产出的 341 条 `spacer_self_fold` 与参考输出**逐字节一致** → 折叠能量与官方 RNAfold 完全等价。
- 另有 `tools/win-shims/python3` shim，把 `python3` 和 `#!/usr/bin/env python3` 指向 conda env。

## tensorflow 2.10 加载 TF 2.14 SavedModel

**成功。** 全部 fold 模型加载仅有警告：
`WARNING:tensorflow:SavedModel saved prior to TF 2.5 detected when loading Keras model...`，
推理正常，最终 `crispron.csv` 与参考输出逐字节一致。兼容赌注成立。

## test.sh 结果

- `CRISPRparams.tsv`：341 条，数值与 `outdir.original` **完全一致**
  （分 4 片并行绕过 300 s 工具时限后按输入顺序重排，逐字节 diff 为空）。
- `crispron.csv`、`23mers.fa`、`30mers.fa`：逐字节一致。
- 按 test.sh 的判定逻辑执行 `diff -r test/outdir.test test/outdir.original`：无任何差异 → **TEST ok**。
- 诚实备注：因 Bash 工具单次 300 s 上限，CRISPRspec 步骤（341 条 guide × 每条一次
  RNAfold 子进程）分片运行再合并，未在一个 300 s 窗口内一口气跑完 `bash bin/test.sh`；
  但执行的步骤与 CRISPRon.sh 完全一致，输出经 diff 验证一致。

## 示例序列打分

输入（`env/crispron_win_example_out/example.fa`）：
```
>example_30bp
ATCGGCTAAGCTAGGCTAGCATCGTGGATC
```
- 提取到 1 条 30mer（plus 链，PAM=TGG，guide=`GCTAAGCTAGGCTAGCATCG`）
- CRISPRoff 特征：RNA_DNA_eng=-29.6, weighted=-54.03, DNA_DNA_opening=27.02,
  spacer_self_fold=-4.8, CRISPRoff_score=22.21
- **CRISPRon 分数 = 59.61**（`env/crispron_win_example_out/crispron.csv`）

## 运行方式（复现）

```bash
export PATH="/d/lifesciencechallenge/cs_pipeline/tools/win-shims:\
/d/lifesciencechallenge/cs_pipeline/tools/ViennaRNA/bin:\
/c/Users/<用户>/anaconda3/envs/crispron-win:\
/c/Users/<用户>/anaconda3/envs/crispron-win/Scripts:$PATH"
cd /d/lifesciencechallenge/cs_pipeline/tools/CRISPRon
bash bin/CRISPRon.sh <input.fa> <outdir>
```

## 遗留问题

- ViennaRNA 官方安装包未能解压/安装，当前 RNAfold 为 shim（数值已验证等价）；
  若后续需要 RNAfold 的完整 CLI 功能（约束折叠、配分函数等），需在可交互会话里
  运行官方安装器或换用 WSL。
- 无 GPU，TF 2.10.1 CPU 推理，速度可接受（341 条 guide 端到端约 6–7 分钟）。
