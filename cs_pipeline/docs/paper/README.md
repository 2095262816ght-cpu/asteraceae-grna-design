# 文献与参考资料索引（docs/paper）

> **说明**：文献 PDF 本地存放于本目录及子目录中，受 `.gitignore` 规则保护不入 git 仓库，团队网盘为长期权威源。  
> 本文提供文献库结构导航、核心论点及与本项目实施方案的对应关系。

---

## 目录结构

```
paper/
├── crispr_grna_core/             # CRISPR gRNA 活性预测与 Hi-TOM 核心文献
│   ├── Chen2022_*                # gRNA 效率算法基准评测（Bioinformatics）
│   ├── Kim2019_*                 # DeepSpCas9 模型（Science Advances）
│   ├── Xiang2021_*               # CRISPRon 效率预测模型
│   ├── Wang2024_*                # 莴苣 T2T 完整参考基因组
│   ├── Liu2019_*                 # Hi-TOM 高通量突变检测原理与解读笔记
│   ├── Du2026_*                  # CRISPR 深度学习方法最新综述
│   ├── Gong2026_*                # 植物特定 gRNA 效率工具评测
│   ├── Li2025_*                  # CRISPR-HNN 混合神经网络
│   └── Zhang2023_*               # CRISPR-AIDIT 活性预测
├── Avsec2025_AlphaGenome.pdf     # 基因组多任务深度基础模型
├── Cao2024_lettuce_domestication_DNA_methylation.pdf # 莴苣驯化全基因组 DNA 甲基化
├── Guo2023_LettuceGDB_database.pdf                   # 莴苣多组学数据库
├── He2026_CLAMP_chromatin_loop_LM.pdf                # 染色质环与 3D 基因组语言模型
├── Lv2026_SeiPlant_histone_cross_species.pdf         # SeiPlant 植物组蛋白修饰跨物种预测
├── Wrightsman2022_cross_species_chromatin_state.pdf  # 跨物种染色质状态与可及性迁移
└── Zhao2021_PlantDeepSEA.pdf                         # 植物非编码变异效应深度学习
```

---

## 一、核心算法与数据源文献（`crispr_grna_core/`）

| 论文标识 | 标题 / 关键贡献 | 项目对应模块 / 落地价值 |
|---|---|---|
| **Kim2019** | *DeepSpCas9* (Science Advances) | **单模型基座 1**：提供了 CNN 结构与预训练权重；本项目封装在 `scripts/predict.py` 与 `app/score_deepspcas9_cli.py`。 |
| **Xiang2021** | *CRISPRon* (Bioinformatics) | **单模型基座 2**：引入 gRNA 结合能 $\Delta G$ 与位置特征；本项目封装在 `scripts/crispron_wsl.py` 中经 WSL 真实推理。 |
| **Chen2022** | *gRNA efficiency algorithms benchmark* (Bioinformatics) | **集成模型立项依据**：证明单一模型无法泛化，Stacking 集成是提升跨体系预测稳健性的最佳路径。 |
| **Wang2024** | *Lettuce T2T Genome* (Plant Communications) | **参考基因组底座**：提供了高精度的莴苣染色体组序列，作为脱靶扫描（`07_scan_lettuce.py`）与候选排序的标准目标。 |
| **Liu2019** | *Hi-TOM: High-throughput Tracking of Mutation* | **测序数据解析原理**：本项目自有橡胶草编辑数据的定性与解码规范，支撑数据清洗 `problem.md` 系列。 |
| **Gong2026** | 植物 CRISPR gRNA 工具评测综述 | 支撑方案调研与竞赛背景陈述，证明目前缺乏植物专用高精度模型的行业痛点。 |
| **Du2026 / Li2025 / Zhang2023** | 深度学习/混合神经网络前沿 | 算法创新性答辩与未来工作展望参考文献。 |

---

## 二、多组学与植物表观组学支撑文献（`paper/` 根目录）

| 论文标识 | 研究内容 | 在多组学实施方案（`multiomics_*`）中的作用 |
|---|---|---|
| **Cao2024** | 莴苣驯化过程中的 DNA 甲基化动态 | 方案 2/3（表观修饰对编辑可及性与组织特异性的调控背景）。 |
| **Guo2023** | LettuceGDB 多组学基因组数据库 | 莴苣组织表达谱数据（`data/expression/`）与基因命名交叉对照的权威信源。 |
| **Avsec2025** | AlphaGenome 统一基因组大模型 | 项目技术演进与植物大模型前瞻背景。 |
| **Lv2026 / Wrightsman2022** | SeiPlant / 植物跨物种染色质状态迁移 | 论证从模式植物向菊科农作物迁移表观特征的科学依据与理论上限。 |
| **Zhao2021** | PlantDeepSEA 非编码变异效应预测 | 脱靶位点功能性影响评定（方案 5）的理论参考。 |
