# 菊科菊苣族 gRNA 设计工具（CS 管线）

DeepSpCas9 + CRISPRon 双模型打分 → 岭回归 Stacking 集成（自有橡胶草 Hi-TOM 数据训练/验证）→ 莴苣 T2T 基因组候选 gRNA 扫描 → Cas-OFFinder 脱靶过滤 → Streamlit demo。

## 目录结构

```
cs_pipeline/
├── env/environment.yml        # conda 环境定义（交付物，必须进 git）
├── data/
│   ├── hitom_clean_v1.csv     # 生物系交付的权威输入（只读快照）
│   ├── hitom_seq30_0909.csv   # 补齐 30bp 上下文后的主表
│   ├── deepspcas9_tableS1.xlsx# 公开数据预案（仅 9.18–9.19 不达标时启用）
│   └── lettuce/               # 莴苣 T2T 基因组 + GFF3 + 着丝粒 bed（不进 git）
├── scripts/                   # 流水线脚本，按编号顺序执行
├── results/                   # 所有产出表与图
├── app/app.py                 # Streamlit demo
└── requirements.txt
```

## 环境搭建

```bash
conda env create -f env/environment.yml   # 主管线环境 crispr（含 genet）
conda activate crispr
```

打分工具链（9.8 实测后按详案降级方案 1 确定，crisprScore 弃用——其 DeepSpCas9 环境 py2.7+TF1.4.1 无 Windows pip 包，且 crisprScore 任何版本均不含 CRISPRon）：

- **DeepSpCas9**：genet 0.17.2（Python/TF2.9，Windows 原生，`crispr` 环境内）
- **CRISPRon**：官方仓库 RTH-tools/CRISPRon（TF2.14），运行于 WSL Ubuntu-22.04 的 `crispron` 环境；一键重建：`wsl -d Ubuntu-22.04 -- bash env/setup_crispron_wsl.sh`
- Streamlit demo 环境独立：`conda env create -f env/environment_demo.yml`（genet 的 protobuf 约束与 streamlit 冲突，打分经子进程调 crispr 环境）
- R 侧 crisprScore 安装脚本保留在 `env/install_crisprscore.R`（含西湖大学 Bioc 镜像配置与 basilisk Windows 补丁 `env/patch_basilisk.R`），仅备用

## 复现流程

按 `scripts/` 编号顺序执行（01 建 seq30 → 02/03 模型打分 → 04 迁移性 D2 → 05 特征 → 06 Stacking 训练 → 07 基因组扫描 → 08 脱靶）。

## 外部工具

- Cas-OFFinder（Windows release 二进制置于 `tools/`，不随代码包发布）
- CRISPRon / CRISPRoff（RTH，GPL/AGPL；仓库克隆与模型文件不入 git，由 `env/setup_crispron_wsl.sh` 重建）

## 数据说明

莴苣 T2T 基因组大文件（`data/lettuce/`）不随代码发布；Hi-TOM 原始数据以团队共享网盘为权威源。
