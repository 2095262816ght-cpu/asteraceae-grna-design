# 菊科菊苣族 CRISPR/Cas9 gRNA 设计与脱靶评估系统

> **第一届全球大学生生命科学挑战赛（赛道二：AI 基因编辑与核酸工具设计）参赛项目**  
> 交付基准版本：`v2.1`（2026-09-25 冻结）

---

## 💡 项目概述与核心亮点

本项目针对植物育种领域（特别是菊科菊苣族：橡胶草、莴苣等）缺乏高质量 gRNA 效率预测工具、人源预训练模型直接迁移存在系统偏差的痛点，构建了面向全基因组扫描、高精度打分、脱靶过滤与多组学时空表达决策的一体化流水线。

1. **首个成规模植物实测金标准数据集（`noB879`）**：
   - 深入审计并治理橡胶草（TKS）Hi-TOM 测序数据（1,368 行 / 24 批次），系统修复 PAM 错记、坐标偏移、链向整列反转、indel 口径低估等 7 类历史问题，剔除多候选竞争未确认样本，构建出 879 行 / 16 基因组的纯 A 级金标准数据集；
   - 根目录下保留的 `_check_*.py` 与 `_fix_*.py` 为数据治理期间的微观读段与坐标对齐可复现审计脚本。
2. **算法突破：分层选择性 Beta-Binomial GLMM（形态二模型）**：
   - 融合预训练双模型（DeepSpCas9 + CRISPRon）与 8 维生物物理特征；
   - 建立选择性经验贝叶斯（Selective EB）批次效应随机截距收缩机制，剥离实验批次扰动，推断纯序列生物学活性；
   - 独立测试集实现正向相关 $\rho = \mathbf{+0.342}$（$p = 7.89 \times 10^{-7}$），低混杂核心折突破至 $\rho = \mathbf{+0.464}$。
3. **全基因组候选扫描与 Cas-OFFinder 脱靶过滤**：
   - 完成莴苣 T2T 完整基因组 45,770 个基因的全外显子与启动子区扫描，产出 1,386.7 万条候选位点；
   - 借助 Cas-OFFinder（GPU/CPU）完成脱靶位点检索与着丝粒抑制区过滤。
4. **多组学时空表达看板与转化窗口决策**：
   - 整合莴苣 5 组织（根、茎、叶、花、种子）均值表达与 16 批生物学重复，提供组织特异性敲除适宜性诊断；
   - 整合橡胶草 S1–S9 发育时相多组织表达谱，量化产胶关键通路（CPT、REF、SRPP）的推荐转化窗口。
5. **交互式 Web 系统（Streamlit）**：
   - 交付开箱即用的 Web 系统：全基因组靶基因输入端（莴苣 45,981 个 `LsT2T1G*` 基因 + 49 个 NLR 代表基因 `LsaT2T01G*` 双注释命名空间，即输即搜），支持候选推荐表过滤下载与自定义 30bp 序列实时打分（WSL CRISPRon 真实调用与降级溯源）。

---

## 🚀 极速启动（Windows 一键运行）

本系统提供全自动化启动脚本，零配置快速体验：

| 方式 | 操作说明 |
|---|---|
| **一键启动 Demo** | 直接双击根目录下的 [`一键启动Demo.bat`](file:///d:/lifesciencechallenge/%E4%B8%80%E9%94%AE%E5%90%AF%E5%8A%A8Demo.bat)（自动检测 Conda 与 Python 环境并拉起浏览器） |
| **一键部署环境（国内源）** | 直接双击根目录下的 [`一键部署_国内源.bat`](file:///d:/lifesciencechallenge/%E4%B8%80%E9%94%AE%E9%83%A8%E7%BD%B2_%E5%9B%BD%E5%86%85%E6%BA%90.bat)（自动通过清华开源镜像安装依赖与权重） |
| **命令行启动** | 在终端激活 `grna-demo` 环境后运行：<br>`cd cs_pipeline && streamlit run app/app.py` |

---

## 📂 项目结构总览

全部核心代码、数据、模型与文档集中于 [`cs_pipeline/`](file:///d:/lifesciencechallenge/cs_pipeline/)：

```text
d:\lifesciencechallenge\
├── 一键启动Demo.bat             # 根目录极速启动入口
├── 一键部署_国内源.bat          # 根目录极速部署入口（清华镜像）
├── README.md                   # 本文件（项目导航总门户）
├── _check_*.py / _fix_*.py     # Hi-TOM 原始测序数据 7 类问题核对与审计脚本（38 个）
└── cs_pipeline/                # 主流水线工程目录
    ├── app/                    # Streamlit Web 应用与打分子进程
    │   ├── app.py              # Web 界面交互主程序
    │   ├── score_deepspcas9_cli.py # 子进程打分通信接口
    │   ├── expression_visualizer.py# 多组织表达看板组件
    │   └── tks_window_visualizer.py# 橡胶草产胶时相决策组件
    ├── scripts/                # 完整流程执行脚本（00–25）
    │   ├── 15_train_hierarchical_bb_nob879.py # 生产模型训练主脚本
    │   ├── 24_model_comparison_nob879.py      # 同口径模型横向对比总表
    │   ├── predict.py          # 官方统一推理预测接口
    │   ├── features_common.py  # 10 维标准特征单一来源模块
    │   ├── hier_bb_model.py    # 分层选择性 Beta-Binomial 模型
    │   └── crispron_wsl.py     # WSL 内原生 CRISPRon 真实调用
    ├── data/                   # 经清洗整理的结构化数据集与表达矩阵
    │   ├── hitom/              # Hi-TOM 测序数据与序列主表
    │   ├── expression/         # 莴苣 5 组织与橡胶草时相多组学表达矩阵
    │   └── demo/               # Web 演示所需代表候选与基因集
    ├── models/                 # 预训练模型权重与离线包
    ├── results/                # 产出评估报告、模型卡与对比表
    │   ├── model_card_hier_bb_nob879_0921.md # 官方生产模型卡（含局限性与 SNP 噪声分析）
    │   ├── model_comparison_nob879_0921.csv  # 官方同口径横向对比总表
    │   ├── CHANGELOG_0927.md   # 指标冻结与变更权威记录
    │   └── offtarget_runlog_0924.md # 脱靶运行审计日志
    ├── env/                    # 环境定义配置（Conda YAML 与初始化脚本）
    ├── docs/                   # 详尽资料库（方案分工、工作报告、文献笔记）
    └── tests/                  # 自动化无头测试套件
```

---

## 📑 关键文档导航

- [流水线技术与复现手册](file:///d:/lifesciencechallenge/cs_pipeline/README.md)：环境搭建、依赖安装、从原始测序到 Web Demo 的全流程复现步骤；
- [项目资料库索引](file:///d:/lifesciencechallenge/cs_pipeline/docs/README.md)：分工详案、工作报告、理论笔记、文献调研与赛事材料总目录；
- [项目全景审计进展报告](file:///d:/lifesciencechallenge/cs_pipeline/docs/project_progress_report.md)：数据治理闭环、模型突破历程、工程阻断闭环与多组学实施方案；
- [生产模型卡（v2.1）](file:///d:/lifesciencechallenge/cs_pipeline/results/model_card_hier_bb_nob879_0921.md)：数据来源、特征定义、评估指标、双 guide 错配说明与已知标签口径局限分析。

---

## 🔒 匿名评审合规声明

本仓库严格遵循第一届全球大学生生命科学挑战赛匿名评审要求：
1. 代码、文档、配置及注释中不包含任何高校名称、院系名称、指导教师与参赛队员个人真实姓名；
2. 彻底剔除所有本地开发机绝对路径与个人用户名；
3. 外部引用工具及公开镜像源（如清华开源软件镜像站）均为公共技术基础设施，不代表参赛单位。
