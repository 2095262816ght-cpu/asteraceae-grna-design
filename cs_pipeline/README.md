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
conda env create -f env/environment.yml
conda activate crispr
# R 侧依赖（R>=4.3）：
#   if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager")
#   BiocManager::install("crisprScore")
```

## 复现流程

按 `scripts/` 编号顺序执行（01 建 seq30 → 02/03 模型打分 → 04 迁移性 D2 → 05 特征 → 06 Stacking 训练 → 07 基因组扫描 → 08 脱靶）。

## 外部工具

Cas-OFFinder（Windows release 二进制置于 `tools/`，不随代码包发布）。

## 数据说明

莴苣 T2T 基因组大文件（`data/lettuce/`）不随代码发布；Hi-TOM 原始数据以团队共享网盘为权威源。
