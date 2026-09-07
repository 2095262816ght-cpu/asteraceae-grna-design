# 进度备忘（9.7 晚暂停，明天从这儿接着干）

## 现状结论

- **计A 分工，项目走主方案不变**。工具层已确认走降级 1（详案 A0 半天原则内）：
  - DeepSpCas9 → **genet**（Python/TF2，Windows 原生）
  - CRISPRon → **官方仓库 RTH-tools/CRISPRon**（WSL Ubuntu-22.04）
  - 原因：crisprScore 的 DeepSpCas9 环境要 py2.7+TF1.4.1，Windows 无解；且 crisprScore **任何版本都没有 CRISPRon**（详案前提有误，需在群里同步更正）

## 已完成

- `cs_pipeline/` 目录按详案 0.4 节建好，git 已初始化（提交者已匿名 team/team@example.com）
- conda 环境 `crispr` 建好（py3.10 + R4.3.3 + 全套包）；samtools 无 win-64 版已剔除，9.20 时用 WSL 的
- **CRISPRon ✅ 已跑通**（WSL `crispron` 环境，TF2.14+ViennaRNA2.6.4）：官方 341 条测试与参考最大偏差 0.01（TF 版本尾差）
- 网络坑已全部排掉：~/.condarc 加了 bioconda→清华镜像；Bioc 用西湖大学镜像；basilisk Windows 激活 bug 已写补丁 `env/patch_basilisk.R`（备用）
- 关键脚本：`env/setup_crispron_wsl.sh`（WSL 一键重建）、`env/install_genet.sh`

## 明天的第一件事

```bash
bash /d/lifesciencechallenge/cs_pipeline/env/install_genet.sh
```

昨晚被掐断在下载 tensorflow-2.9.3（444MB，genet 锁 TF<2.10），pip 缓存已有 1.1GB，重跑会断点续传，预计几分钟装完。看到日志末尾 `GENET_DEEPSPCAS9_OK` 即成功，A0 收工。

## 之后

1. 把 `scripts/02`（DeepSpCas9）改写为调 genet 的 Python 版；`scripts/03`（CRISPRon）改写为 WSL 封装版（产出 CSV 列名不变：guide_id + 分数）
2. 等生物系交付 `hitom_clean_v1.csv` + 橡胶草参考基因组 fasta（放 `cs_pipeline/data/`）→ 跑 01 出 `hitom_seq30_0909.csv`
3. 9.20 前记得：莴苣基因组境外下载走 Windows 侧代理，WSL（NAT）用不了 localhost 代理

## 注意

- WSL 命令必须从脚本文件执行（wsl.exe 会拆散多行 -c 字符串）；Windows 路径传 WSL 时用 `MSYS_NO_PATHCONV=1`
- genet 的 DeepSpCas9 API 还没实测过，02 脚本写完先用示例序列对一下再批量跑
