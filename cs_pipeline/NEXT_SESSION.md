# 进度备忘（9.8 更新）

## A0 已收工：两个模型都能打分

- ✅ conda 环境 `crispr`（py3.10 + R4.3.3 + genet 0.17.2/TF2.9.3）
- ✅ DeepSpCas9：`scripts/02_score_deepspcas9.py`（genet `SpCas9().predict(list_of_seq30)` → DataFrame[Target, Spacer, SpCas9]，示例分 71.25）
- ✅ CRISPRon：WSL `crispron` 环境 + 官方仓库（`tools/CRISPRon`），官方测试 341 条与参考最大偏差 0.01；`scripts/03_score_crispron.py`（Windows 侧入口，内部调 WSL）

## 待办（按优先级）

1. **等生物系交付** `hitom_clean_v1.csv` + 橡胶草参考基因组 fasta（放 `cs_pipeline/data/`）→ 跑 01 → 02/03
2. **git 匿名化问题（提交前必须处理）**：仓库在根目录 `D:\lifesciencechallenge`，root 提交作者是 `2095262816ght-cpu`（疑似学号+机器名，踩 10.3 红线）。处理方案：git filter-repo 重写作者，或交付时删 `.git` 只交快照（详案认可的退路）
3. 02/03 脚本尚未用真实数据跑过（缺生物系数据）；02 已用示例序列验证 genet API
4. `streamlit` 与 genet 的 protobuf 冲突：demo 环境独立为 `env/environment_demo.yml`，9.25 计B 用；predict 调用走子进程进 crispr 环境
5. genet 装完把 numpy 降到 1.26.4，pandas/sklearn 已验证兼容

## 排过的坑（备忘）

- crisprScore 弃用原因：DeepSpCas9 环境 py2.7+TF1.4.1 无 Windows pip 包；crisprScore 任何版本均无 CRISPRon（详案前提有误，已同步更正口径）
- 镜像配置：~/.condarc 加了 bioconda→清华；Bioc 包用西湖大学镜像；pypi 用清华
- basilisk Windows 激活 bug（子进程 Rscript 找不到 DLL，exit 309）：补丁 `env/patch_basilisk.R` 备用
- samtools 无 win-64 版：9.20 用 WSL（Ubuntu-22.04 已装 miniconda）或 Windows 二进制
- WSL 调用纪律：脚本必须从文件执行（wsl.exe 会拆散多行 -c）；Windows 路径传 WSL 用 `MSYS_NO_PATHCONV=1`
- genet 使用 TF2.9.3（锁 <2.10）；首次 predict 自动从 GitHub 下载模型 checkpoint（约 700KB，走系统代理）
