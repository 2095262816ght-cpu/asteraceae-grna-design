# 进度备忘（9.8 更新）

## A0 已收工：两个模型都能打分

- ✅ conda 环境 `crispr`（py3.10 + R4.3.3 + genet 0.17.2/TF2.9.3）
- ✅ DeepSpCas9：`scripts/02_score_deepspcas9.py`（genet `SpCas9().predict(list_of_seq30)` → DataFrame[Target, Spacer, SpCas9]，示例分 71.25）
- ✅ CRISPRon：WSL `crispron` 环境 + 官方仓库（`tools/CRISPRon`），官方测试 341 条与参考最大偏差 0.01；`scripts/03_score_crispron.py`（Windows 侧入口，内部调 WSL）

## 数据情况更新（老师 9.9 反馈）

- 数据结构：一个靶点转化出多个单株，每株测一次编辑效率 → **行数多（约上千）、唯一靶点少**；同靶点跨株系一致性好（"要么都好要么都差"），验证了"序列决定效率"的前提
- 有效样本量 = 唯一靶点数（同靶点各行 seq30 相同、模型打分相同，只是重复测量）。D1 档位按唯一靶点数定档
- **待问老师**：① 共有多少条不同 gRNA（唯一靶点数，决定 D1 档位）；② 是否所有单株（含低效率被淘汰的）都有测量记录
- 给生A：同一靶点的每个单株各占一行，guide_id 相同、rep 填单株序号；**低效率单株的记录必须保留，不能只留被选中的株**（否则标签系统性偏高）
- 计A 待改：04/05 前加一步按 guide_id 聚合（mean + n_lines + sd）；训练/测试划分按 guide_id 分组（同靶点所有单株进同一侧），gene_id 分组作为外层。两层防泄漏，正好是 PPT 第 10 页素材

## 待办（按优先级）

1. **等生物系交付** `hitom_clean_v1.csv` + 橡胶草参考基因组 fasta（放 `cs_pipeline/data/`）→ 跑 01 → 02/03
2. **git 匿名化（已定案）**：不重写历史、不换账号；10.2 打包时删除 `.git` 目录只交代码快照（详案 10.3 清单认可的方式）。交付前提醒一次
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
