# 分工详案：计算机系两人（计A / 计B）

> 依据：《项目执行方案_v3压缩版_0907》（docs/plans/project_plan_v3_condensed_0907.md）《项目技术要点笔记》（docs/knowledge/project_tech_notes.md）《两篇CRISPR文献详细解读》（docs/knowledge/CRISPR_core_papers_notes.md）
> 硬约束：每天约 3 小时/人；10 月 4 日区赛提交硬截止；任何阶段超期 2 天以上触发砍项（先砍 demo 美化，保留命令行+结果表）。
> 环境：Windows + Anaconda Prompt / Git Bash。所有命令均在此两终端可跑；R 命令在 Anaconda Prompt 内 `Rscript` 执行。

---

## 0. 总览

### 0.1 角色与边界

| 代号 | 角色 | 负责阶段 | 一句话职责 |
|---|---|---|---|
| 计A | 模型负责人 | 阶段 1（9.10–9.12）、阶段 2（9.13–9.19） | 预训练模型打分 → 迁移可行性结论 → Stacking 岭回归集成模型，交出"模型 + 指标" |
| 计B | 管线与工具负责人 | 阶段 3（9.20–9.26）、10.2 打包 | 莴苣 T2T 基因组扫描 → Cas-OFFinder 脱靶 → Streamlit demo，交出"工具 + demo" |

计A 的产出（集成模型）是计B demo 的打分引擎；两人接口是 `cs_pipeline/results/meta_model_ridge_0919.joblib` + 打分函数约定（见 0.4）。

### 0.2 技术路线与红线（不可擅自变更）

```
DeepSpCas9 打分 ─┐
CRISPRon 打分 ───┼→ 特征矩阵 → 岭回归元模型(Stacking) → 自有橡胶草Hi-TOM数据训练/验证
                 │                                        │
                 └──────── 莴苣T2T基因组扫描候选gRNA → 模型打分 → Cas-OFFinder脱靶过滤 → Streamlit demo
```

红线（主方案 v3 已明确砍掉，任何"顺手做一下"都要先问团队）：

- ❌ 不走微调主线。仅当 9.8 数据盘点 ≥300 条 **且** 9.19 前 Stacking 已达标、还有富余时间，才可作为加分项尝试；本项目默认不碰模型权重。
- ❌ 不复现原版 DeepSpCas9 TF1.x 代码。只用维护良好的封装：首选 R 包 **crisprScore**（Bioconductor，同时提供 DeepSpCas9 和 CRISPRon 打分函数），备选 Python 包 **genet**（pip，提供 DeepSpCas9）。
- ⚠️ 默认只用两个模型。DeepHF 是主方案保留的可选加分项，非主线；仅当 9.19 达标且时间富余、经全队确认后才可启用（CRISPR-AIDIT / CRISPR_HNN 仍不加）。两个模型足够做 Stacking，多一个模型多一份环境风险。
- ❌ 不做序列扰动扩增、不做 GAN/VAE 造数据（生物学上错误，见技术要点笔记 §6）。
- ✅ 唯一允许的扩充预案：DeepSpCas9 Table S1 公开数据加权混合（仅限 9.18–9.19 指标不达标时启用，1 天上限）。

### 0.3 里程碑日历

| 日期 | 计A | 计B | 两人共同 |
|---|---|---|---|
| 9.7–9.8 | 待命，配合生物系确认数据格式 | 待命；预研 Cas-OFFinder 版本 | — |
| 9.9 | 建环境、跑通示例打分 | 协助（装第二套备用环境） | — |
| 9.10–9.11 | DeepSpCas9 / CRISPRon 打分 | 协助核对坐标取向 | — |
| 9.12 | 算 Spearman ρ，写 D2 结论 | 参与 | 🔶 D2 决策点 |
| 9.13–9.19 | Stacking 训练与评估 | 预研基因组下载镜像预案与 Cas-OFFinder 部署（GFF 解析原型排在 9.21） | — |
| 9.20–9.23 | 收尾、支援计B | 莴苣基因组扫描脚本；回填 nlr_genes_514.csv 坐标（9.24 前交回生B） | — |
| 9.24 | 支援 | Cas-OFFinder 脱靶预测 | — |
| 9.25–9.26 | 把模型封装给 demo | Streamlit demo | — |
| 9.27 | 指标冻结 | 指标冻结 | ✅ 冻结所有数字+代码 |
| 9.28–10.1 | 报告/视频配合（生物系主导） | 报告/视频配合 | — |
| 10.2 | 源码自查 | 源码打包 | — |
| 10.3 | 匿名化检查 | 匿名化检查 | ✅ 匿名化专项检查 |
| 10.4 | 提交 | 提交 | ✅ 全天纯容错 |

### 0.4 公共约定（目录、列名、接口）

项目工作目录统一为 `<项目根>\cs_pipeline\`，结构如下（9.9 由计A创建并初始化 git 仓库，注意：**不进 git 的目录写入 .gitignore**：`data/lettuce/` 基因组大文件、`env/` 下的缓存（`env/environment.yml` 本身必须进 git，它是交付物））：

```
cs_pipeline/
├── env/
│   └── environment.yml                # conda 环境定义
├── data/
│   ├── hitom_clean_v1.csv             # 生物系 9.9 晚交付（唯一权威输入；网盘 LSC_共享/data/hitom/ 为权威源，本目录为只读快照）
│   ├── hitom_seq30_0909.csv           # 计A 9.9 产出：补齐30bp上下文
│   ├── deepspcas9_tableS1.xlsx        # 9.11 下载备用（公开数据预案）
│   └── lettuce/
│       ├── lettuce_t2t.fa             # 莴苣T2T基因组（~2.59Gb）
│       ├── lettuce_t2t.fa.fai         # 索引
│       ├── lettuce_t2t.gff3           # 注释
│       └── centromere_regions.bed     # 着丝粒区坐标（生物系 9.23 晚交付，F3）
├── scripts/
│   ├── 01_build_seq30.py
│   ├── 02_score_deepspcas9.R
│   ├── 03_score_crispron.R
│   ├── 04_spearman_D2.py
│   ├── 05_features.py
│   ├── 06_train_stacking.py
│   ├── 07_scan_lettuce.py
│   └── 08_casoffinder_run.sh
├── results/                           # 所有产出表与图（精确文件名见各节）
├── app/
│   └── app.py                         # Streamlit demo
├── README.md
└── requirements.txt
```

**与生物系的接口约定（9.9 晚 24:00 前交付 `hitom_clean_v1.csv`）**：

CSV，UTF-8 编码，每行一条 gRNA，列名固定为：

| 列名 | 含义 | 示例 | 备注 |
|---|---|---|---|
| `guide_id` | 唯一编号 | TKS_0001 | 不允许重复 |
| `gene_id` | 基因编号 | TKS_g00123 | **分组划分训练/测试集的依据，必须有** |
| `seq20` | 20nt 引导序列 | GCTAAGC…（20bp） | 5'→3'，与 PAM 相邻 |
| `pam` | 3nt PAM | TGG | 必须 NGG，不符合的整行剔除并告知生物系 |
| `chrom` | 染色体/scaffold | Chr1 | 与橡胶草参考基因组序列名完全一致 |
| `start` / `end` | 靶位点坐标 | 10234 / 10256 | 已定稿：1-based 闭区间，start/end = seq20+PAM 合并区间共 23nt |
| `strand` | 链方向 | + / - | 坐标取向错误的头号来源 |
| `batch` | 实验批次 | B202503 | 供批次归一化 |
| `rep` | 生物学重复 | 1 | 无重复则全填 1 |
| `indel_pct` | Hi-TOM 实测突变率 | 42.3 | 数值，百分数（0–100），不是小数 |
| `efficiency_norm` | 批次内百分位效率 | 68.5 | 0–100 数值，生A 已算好（Excel PERCENTRANK.INC），直接使用，不得重算 |

生物系另需交付：莴苣基因组文件（9.20–9.21，见 B1 节）、`centromere_regions.bed`（9.23 晚，三列：chrom、start、end）。另有 `nlr_genes_514.csv` 的坐标回填流转：生B 9.23 晚交计B → 计B 用 GFF 按 gene_id 回填坐标 → 9.24 前交回生B 抽查（见 B2 节）。

**计A → 计B 的模型接口（9.17）**：计A 提供 `scripts/predict.py`，暴露一个函数：

```python
def predict_efficiency(seq30_list: list[str]) -> list[float]:
    """输入30bp序列（4nt上游+20nt guide+3nt PAM+3nt下游），返回集成模型预测分数（与indel_pct同尺度的相对分数）。"""
```

计B 只调这个函数，不接触模型内部。模型文件 `results/meta_model_ridge_0919.joblib` 与公开模型打分由 predict.py 内部加载。

---

## 1. 计A 详案：模型负责人（9.9–9.19）

### A0 · 9.9（周三）建环境，跑通示例打分

**目标**：一个 conda 环境 + R 环境，crisprScore 能对一条示例 30bp 序列打出 DeepSpCas9 分。

**3 小时安排**：
- 第 1 小时：建 conda 环境（含 Python 3.10、R 4.3、pandas、scikit-learn、biopython、matplotlib、joblib）；
- 第 2 小时：装 crisprScore（Bioconductor），跑示例；
- 第 3 小时：跑不通则启动降级链（见下）；跑通则处理 `hitom_clean_v1.csv` → 生成 `hitom_seq30_0909.csv`。

**环境命令（Anaconda Prompt）**：

```bash
cd /d <项目根>\cs_pipeline
conda create -n crispr python=3.10 r-base=4.3 pandas scikit-learn biopython matplotlib joblib r-essentials -c conda-forge -y
conda activate crispr
```

**crisprScore 安装（R 内执行）**：

```r
# Anaconda Prompt 中先执行 R 进入交互界面，或写进 install.R 用 Rscript install.R
if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager")
BiocManager::install("crisprScore")   # 依赖较多，首次约20-40分钟，耐心等
library(crisprScore)
# 示例验证：30bp = 4nt上游 + 20nt guide + 3nt PAM + 3nt下游
getDeepSpCas9Scores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC")  # 返回一个数值即成功
getCRISPRonScores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC")
```

> crisprScore 底层用 basilisk 自动管理 Python 依赖（TF2 版 DeepSpCas9），首次调用会自动下载一个隔离 conda 环境，需要联网，可能再花 10–20 分钟——这是正常的，不算"装不上"。

**半天原则（装不上就换，9.9 中午 12 点为切换死线）**：

| 顺序 | 方案 | 说明 |
|---|---|---|
| 首选 | crisprScore（R） | 一个包同时给 DeepSpCas9 + CRISPRon，接口统一 |
| 降级 1 | genet（Python）：`pip install genet` | 提供 DeepSpCas9；CRISPRon 改用官方仓库 `git clone https://github.com/RTH-tools/crispron`，按其 README 的 TF2 环境跑 |
| 降级 2 | 只保 CRISPRon 一个模型 | 两个模型都做不成时的底线；Stacking 退化为"单模型分 + 序列特征"的岭回归，叙事改为"以 CRISPRon 为骨架的植物适配校准"，报告仍可写 |

⚠️ 若走到降级 2，9.9 当晚必须在群里告知全队，影响 9.12 D2 结论的措辞。

**产出文件**：
- `env/environment.yml`（用 `conda env export --no-builds > env/environment.yml` 生成）；
- `data/hitom/hitom_seq30_0909.csv`：在生物系表格基础上新增 `seq30` 列（4nt 上游 + seq20 + pam + 3nt 下游，长度恰好 30，全大写，只含 ACGT）。

**从基因组坐标补 30bp 上下文（`scripts/01_build_seq30.py` 骨架）**：

```python
import pandas as pd
from Bio import SeqIO

genome = SeqIO.to_dict(SeqIO.parse("data/reference_genomes/2-1_TKS.genome.fasta", "fasta"))  # 橡胶草参考基因组（生物系 9.9 前提供，生A 负责）
df = pd.read_csv("data/hitom/hitom_clean_v1.csv")

def get_seq30(row):
    """start/end 已定稿：1-based 闭区间，为 seq20+PAM 合并区间共 23nt。
    seq30 = 4nt上游 + seq20 + pam + 3nt下游（沿 guide 5'→3' 方向）。
    +链：取基因组 [start-4, end+3]（1-based），即切片 [start-5 : end+3]；
    -链：取基因组 [start-3, end+4]，即切片 [start-4 : end+4]，再反向互补。"""
    chrom = genome[row.chrom]
    if row.strand == "+":
        s = chrom.seq[row.start - 5 : row.end + 3]
    else:
        s = chrom.seq[row.start - 4 : row.end + 4].reverse_complement()
    return str(s).upper()

df["seq30"] = df.apply(get_seq30, axis=1)
assert df.seq30.str.len().eq(30).all() and df.seq30.str.fullmatch(r"[ACGT]{30}").all()
# 自校验：seq30 的第 5–24 位必须等于 seq20，第 25–27 位必须等于 pam
assert (df.seq30.str[4:24] == df.seq20).all() and (df.seq30.str[24:27] == df.pam).all()
df.to_csv("data/hitom/hitom_seq30_0909.csv", index=False)
```

**验收标准**：示例序列能打出两个模型的分；`hitom_seq30_0909.csv` 行数 = 生物系交付行数，seq30 全部通过断言。自校验断言是防"坐标取向搞反"的第一道防线（D2 复盘时 ρ<0.2 的头号嫌疑就是它）。

---

### A1 · 9.10–9.11（周四、五）两个模型对 Hi-TOM 数据打分

**输入格式细节（两个模型一致，记死）**：

```
seq30 = [4nt 上游上下文][20nt 引导序列][NGG PAM 3nt][3nt 下游上下文]
位置:    1-4              5-24            25-27        28-30
```

DeepSpCas9 与 CRISPRon 都吃这个 30nt 布局，一列 `seq30` 两用。PAM 的 N 也包含在内（位置 25）。

**9.10：DeepSpCas9 打分（`scripts/02_score_deepspcas9.R`）**

```r
library(crisprScore)
df <- read.csv("data/hitom/hitom_seq30_0909.csv")
df$deepspcas9_score <- getDeepSpCas9Scores(df$seq30)
write.csv(df[, c("guide_id", "deepspcas9_score")],
          "results/scores_deepspcas9_0910.csv", row.names = FALSE)
```

- 第 1 小时：跑通 + 打分（几百条数据秒级完成，大量时间花在首次 basilisk 环境初始化）；
- 第 2 小时：抽查 5 条序列，手工核对 seq30 与基因组浏览器/原序列一致（计B 协助）；
- 第 3 小时：画分数分布直方图存 `results/hist_deepspcas9_0910.png`，若分数全部挤在一个极窄区间（标准差 < 1）说明输入格式可能有误，停下来排查。

**9.11：CRISPRon 打分 + 下载备用公开数据**

- 第 1 小时：`scripts/03_score_crispron.R`（同上，函数换 `getCRISPRonScores`），产出 `results/scores_crispron_0911.csv`；
- 第 2 小时：下载 DeepSpCas9 论文 Table S1（12,832 条训练集，Science Advances 官网补充材料页，浏览器下载），存 `data/deepspcas9_tableS1.xlsx`——这是 9.18–9.19 不达标预案的唯一弹药，先备着；
- 第 3 小时：把两个打分表与主表合并成 `results/scores_merged_0911.csv`（guide_id 为键），画两模型分数散点图，初步目测相关性。

**产出文件**：`results/scores_deepspcas9_0910.csv`、`results/scores_crispron_0911.csv`、`results/scores_merged_0911.csv`、`results/hist_*.png`、`data/deepspcas9_tableS1.xlsx`。

**验收标准**：两张打分表行数与主表一致、无 NA；若某个模型对 >5% 的序列返回错误/NA，必须查明原因（通常是 seq30 含 N 或长度不对），不得带着 NA 进入 9.12。

---

### A2 · 9.12（周六）🔶 D2 决策点：迁移可行性结论

**3 小时安排**：
- 第 1 小时：写 `scripts/04_spearman_D2.py`，算 DeepSpCas9 / CRISPRon 打分 vs 归一化实测效率（F1 表 `efficiency_norm` 列，生A 已算好的批次内百分位，见下）的 Spearman ρ 及 p 值；
- 第 2 小时：与计B 一起按分档表得出结论，写 `results/transferability_D2_0912.md`；
- 第 3 小时：把结论同步给全队（生物系报告要用这组数字）。

**批次内归一化（先归一化再算 ρ，顺序不能反）**：

归一化已由生A 在数据交付阶段完成——F1 表自带 `efficiency_norm` 列（批次内百分位，0–100，Chen2022 案例研究同款做法，消除批次效应）。本脚本直接读该列算 ρ，**一律不得用 `indel_pct` 重算**：

```python
import pandas as pd
from scipy.stats import spearmanr

df = pd.read_csv("results/scores_merged_0911.csv")
# efficiency_norm 随 hitom_clean_v1.csv 合并进来，直接使用

for col in ["deepspcas9_score", "crispron_score"]:
    rho, p = spearmanr(df[col], df["efficiency_norm"])
    print(f"{col}: Spearman rho = {rho:.3f}, p = {p:.2e}")
```

**ρ 分档与行动表（D2 决策依据，参照 Chen2022 的 0.3–0.5 单模型正常区间）**：

| 两模型 ρ 范围 | 结论 | 行动 |
|---|---|---|
| ≥ 0.3 | 迁移规律存在，正常水平 | 按原计划进入 Stacking（9.13），预期集成后 ≥0.5 |
| 0.2 – 0.3 | 偏弱但有信号 | 继续 Stacking，但特征工程加重（9.13 多加序列特征），9.19 达标线不变 |
| < 0.2 | 先怀疑 bug 再怀疑生物学 | 当天检查：① seq30 坐标/链取向（最高频错误）② PAM 是否 NGG ③ 效率列单位（% 还是小数）④ `efficiency_norm` 列是否缺失/漏带（归一化由生A 在 F1 表完成，CS 只检查不重算）。**加做动物数据复现自检**：用同一管线给 DeepSpCas9 Table S1 随机抽 2,000 条打分算 ρ，与文献值（≈0.5）对比——动物数据正常 → 确认是迁移问题；动物数据也低 → 管线仍有隐藏 bug，继续排查（弹药已在 `data/deepspcas9_tableS1.xlsx`，约半天）。修正后重算；**仍 <0.2**：进入"如实报告"路线——Stacking 照做，但报告叙事侧重工具链价值与"跨体系迁移失效"这一发现本身（Chen2022 里 U6→T7 也掉到 0.07–0.32，这是有文献背书的正当发现） |

**产出文件**：`results/transferability_D2_0912.md`（含 ρ、p 值、散点图、分档结论与后续行动）、`results/scatter_D2_*.png`。

**验收标准**：结论文档中每个模型的 ρ 都能由 `04_spearman_D2.py` 一键复现；D2 结论在群里获得全队确认（尤其生物系，他们写报告要用）。

---

### A3 · 9.13–9.14（周日、一）特征矩阵组装

**9.13 第 1–3 小时**：写 `scripts/05_features.py`，产出 `results/feature_matrix_0913.csv`。

特征列（在 `scores_merged_0911.csv` 基础上追加）：

| 特征列 | 计算方式 | 生物学依据 |
|---|---|---|
| `deepspcas9_score`, `crispron_score` | 已有 | Stacking 第一层打分（核心特征） |
| `gc_total` | seq20 中 G+C 占比 | 40–60% 区间效率最高（中间最优特征） |
| `gc_seed` | seq20 的 PAM 近端 6nt（位置 19–24 of seq30）GC 占比 | 种子区结合稳定性 |
| `tm` | `Bio.SeqUtils.MeltingTemp.Tm_NN(seq20)` | 最近邻解链温度，局部解链难易 |
| `pam_n` | PAM 第 1 位碱基（A/C/G/T 做 one-hot 四列） | PAM 变体效应 |
| `poly_t` | seq20 是否含连续 ≥4 个 T（0/1） | poly-T 终止转录 |

```python
import pandas as pd
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.MeltingTemp import Tm_NN

df = pd.read_csv("results/scores_merged_0911.csv")
df["gc_total"] = df.seq20.map(lambda s: gc_fraction(s))
df["gc_seed"]  = df.seq30.str[18:24].map(gc_fraction)   # seq30位置19-24 = PAM近端6nt
df["tm"]       = df.seq20.map(Tm_NN)
df["poly_t"]   = df.seq20.str.contains("TTTT").astype(int)
df = pd.concat([df, pd.get_dummies(df.pam.str[0], prefix="pam_n")], axis=1)
df.to_csv("results/feature_matrix_0913.csv", index=False)
```

**9.14**：质量检查 + 冻结特征表。
- 第 1 小时：画每个特征 vs `efficiency_norm` 的相关性条形图 `results/feature_corr_0914.png`（给报告用，也顺便看哪些特征有信号）；
- 第 2 小时：检查特征缺失、量纲、常数列（全 0 或全同值的列删掉）；
- 第 3 小时：冻结为 `results/feature_matrix_0914.csv`（此后训练只读这个文件，特征不再改动——9.27 指标冻结的前置约定）。

**验收标准**：特征矩阵列数 12±4，无 NA、无常数列；`feature_corr_0914.png` 已产出。

---

### A4 · 9.15–9.17（周二、三、四）岭回归元模型训练（防泄漏是评审检查点）

**核心纪律**：
1. **按 `gene_id` 分组划分训练/测试集**，绝不随机切分——同一基因上相邻 gRNA 序列高度相似，随机切分 = 测试集泄题，评审会查；
2. alpha 调参只在训练集内做（嵌套交叉验证），测试集一次都不许碰；
3. 评估主指标 Spearman ρ，副指标 AUC（按效率排序前 20% = 1、后 20% = 0，中间弃用——Chen2022 做法）。

**9.15：分组划分 + 基线（`scripts/06_train_stacking.py` 骨架）**

```python
import numpy as np, pandas as pd, joblib
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, GridSearchCV, LeaveOneGroupOut
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import roc_auc_score

df = pd.read_csv("results/feature_matrix_0914.csv")
FEATS = [c for c in df.columns if c.startswith(("deepspcas9", "crispron", "gc_", "pam_n_"))
         or c in ("tm", "poly_t")]
X, y, groups = df[FEATS].values, df["efficiency_norm"].values, df["gene_id"].values

# 外层：按基因分组的 8:2 划分（固定 random_state=42，全队统一）
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
tr, te = next(gss.split(X, y, groups))

# 内层：仅训练集内 GroupKFold 调 alpha
gs = GridSearchCV(Ridge(), {"alpha": np.logspace(-3, 3, 13)},
                  cv=GroupKFold(5).split(X[tr], y[tr], groups[tr]),
                  scoring="neg_mean_squared_error")
gs.fit(X[tr], y[tr])
best = gs.best_estimator_

# 测试集上：集成 vs 单模型对比
pred_ens = best.predict(X[te])
rho_ens, _ = spearmanr(pred_ens, y[te])
for name, col in [("DeepSpCas9", "deepspcas9_score"), ("CRISPRon", "crispron_score")]:
    rho_single, _ = spearmanr(df[col].values[te], y[te])
```

- 第 1 小时：跑通划分与基线，打印 `len(set(groups[tr]) & set(groups[te]))` 必须 = 0（断言写进脚本，防泄漏自检）；
- 第 2 小时：GridSearchCV 选 alpha，记录 `gs.best_params_` 到结果文件；
- 第 3 小时：AUC 分支——构造 top20/bottom20 标签，用集成模型预测分直接算 `roc_auc_score`（回归分数也可当分类器打分用），再训一个 LogisticRegression 对照。

**9.16：留一基因交叉验证（LOGO-CV）**

```python
logo = LeaveOneGroupOut()
rows = []
for i, (tr_i, te_i) in enumerate(logo.split(X, y, groups)):
    m = Ridge(alpha=gs.best_params_["alpha"]).fit(X[tr_i], y[tr_i])
    rho, _ = spearmanr(m.predict(X[te_i]), y[te_i])
    rows.append({"held_out_gene": groups[te_i][0], "rho": rho})
pd.DataFrame(rows).to_csv("results/logo_cv_0916.csv", index=False)
```

- 第 1 小时：跑 LOGO-CV（数据量 < 300 条时秒级跑完）；若基因数 < 5 导致 LOGO 无意义，退化为 GroupKFold(3) 并在结果中注明；
- 第 2 小时：汇总 LOGO 的 ρ 分布（中位数、四分位），画箱线图 `results/logo_cv_box_0916.png`；
- 第 3 小时：写 `results/training_log_0916.md`，记录划分方式、alpha、各指标——**9.27 指标冻结时以这份日志为准**。

**9.17：收尾与复核**
- 第 1 小时：把最终模型 `joblib.dump(best, "results/meta_model_ridge_0919.joblib")`（文件名保留 0919，9.19 最终确认后不改动）；
- 第 2 小时：写 `scripts/predict.py`（按 0.4 节接口约定，内部串联 crisprScore 打分 → 特征计算 → 岭回归），这是交给计B 的钥匙，当天发给计B 试跑；
- 第 3 小时：自查数据泄漏：全代码搜一遍，确认测试集索引 `te` 没有出现在任何 `fit`/`transform`/`GridSearchCV` 调用里。

**验收标准**：`meta_model_ridge_0919.joblib` 生成；`training_log_0916.md` 含 alpha、训练/测试基因列表、LOGO 结果；泄漏自检断言全部通过。

---

### A5 · 9.18–9.19（周五、六）评估对比 + 达标判定

**9.18：单模型 vs 集成模型对比表 + 散点图**

产出 `results/model_comparison_0919.csv`：

| model | spearman_rho_test | auc_test | rho_logo_cv_median |
|---|---|---|---|
| DeepSpCas9 单用 | … | … | — |
| CRISPRon 单用 | … | … | — |
| Stacking 岭回归（本工作） | … | … | … |

另加一行**动物基准对照**：同批模型在 DeepSpCas9 Table S1（抽样 2,000 条）上的复现 ρ（或文献值 ≈0.5），与自有植物数据 ρ 并排——这条"动物基准 → 植物迁移后 → Stacking 追回幅度"的三段曲线是报告/PPT 的对照叙事素材，也是迁移失效时的归因证据。

散点图 `results/scatter_ensemble_vs_best_0919.png`：左图集成模型预测 vs 实测，右图最强单模型预测 vs 实测（测试集点，配 ρ 标注）。

- 第 1–2 小时：生成表和图（matplotlib，字号调大，直接可用进 PPT）；
- 第 3 小时：对照达标线判定（见下）。

**达标线：测试集 Spearman ρ ≥ 0.5**（主方案 v3 阶段 2 明确）。

| 结果 | 行动 |
|---|---|
| ρ ≥ 0.5 | ✅ 达标。9.19 全天：写 `results/model_card_0919.md`（方法、指标、图、局限），收工进入支援计B |
| ρ < 0.5 | 先回 D2 检查清单排除 bug，确认非管线问题后**当天启用**公开数据加权混合（9.19 一天内完成，见下）；混合后仍 <0.5 → 如实报告 + 叙事侧重工具链（与 9.12 的 <0.2 分支同理），**不再追加任何模型或数据** |

**公开数据加权混合预案（仅不达标时，9.19 一天内完成）**：

```python
# Table S1: 12,832条人源数据，seq30同源格式，标签为indel频率
pub = load_table_s1("data/deepspcas9_tableS1.xlsx")      # 需先跑同一套打分+特征管线
X_all = np.vstack([X[tr], pub[FEATS].values])
y_all = np.concatenate([y[tr], pub["indel_pct"].rank(pct=True).values * 100])  # 公开数据无 efficiency_norm 列，按全表百分位折算到同尺度
w = np.concatenate([np.full(tr.size, 50.0),              # 自有数据权重50
                    np.ones(len(pub))])                  # 公开数据权重1
m = Ridge(alpha=gs.best_params_["alpha"]).fit(X_all, y_all, sample_weight=w)
rho_mixed, _ = spearmanr(m.predict(X[te]), y[te])        # 评估仍只用自有测试集
```

注意：混合预案只改训练数据，**测试集永远只有自有 Hi-TOM 数据**，这点写进报告防评审质疑。

**验收标准**：`model_comparison_0919.csv` 三个模型的 ρ/AUC 齐全；散点图可用于 PPT；达标或预案执行完毕（有明确记录用了还是没用、为什么）。

---

## 2. 计B 详案：管线与工具负责人（9.20–10.2）

### B1 · 9.20–9.21（周日、一）莴苣基因组获取与索引

- 9.20 第 1 小时：**请生物系同学在自己浏览器**从 Figshare 下载莴苣 T2T 基因组 fasta 和 GFF3 注释（主方案提示：Figshare 链接在部分网络环境 403，浏览器通常可开；这是与生物系的接口，当天在群里盯进度）；
- 9.20 第 2–3 小时：文件落盘到 `data/lettuce/`，建索引：

```bash
conda activate crispr
conda install -c bioconda pyfaidx samtools -y
cd /d <项目根>\cs_pipeline
samtools faidx data/reference_genomes/3-1_LsT2T.genome.fa        # 生成 .fai 索引，2.59Gb 约几分钟
python -c "from pyfaidx import Fasta; f=Fasta('data/reference_genomes/3-1_LsT2T.genome.fa'); print(len(f.keys()), '条序列')"
```

- 9.21：写 GFF 解析原型，统计基因/外显子数量，打印前 5 个基因坐标，与生物系核对注释文件里 feature 命名（有的 GFF 用 `mRNA` 有的用 `transcript`，必须先看实际文件再写死）。

**验收标准**：`.fai` 存在；pyfaidx 能随机取任意染色体任意区间的序列（抽 3 个区间与 `samtools faidx chr:start-end` 结果比对一致）。

---

### B2 · 9.22–9.23（周二、三）gRNA 扫描脚本

**设计原则（2.59Gb 大基因组，禁止暴力全基因组扫描）**：
- 只扫描**基因区**：每个基因的启动子（TSS 上游 2000bp，按链方向取）+ 所有外显子。莴苣约 4 万个基因 × 平均 4kb ≈ 160Mb，仅为全基因组的 ~6%；
- 用 pyfaidx 随机访问取序列，不把 2.59Gb 整个读进内存；
- 候选 gRNA 枚举规则：正链找 `NGG`（正则前瞻匹配），取上游 20nt；负链找 `CCN`，取下游 20nt 后反向互补。

**`scripts/07_scan_lettuce.py` 骨架**：

```python
import re, pandas as pd
from Bio.Seq import Seq
from pyfaidx import Fasta

GFF_COLS = ["chrom","source","feature","start","end","score","strand","frame","attr"]
gff = pd.read_csv("data/reference_genomes/3-1_LsT2T.annotation.gff3", sep="\t", comment="#",
                  header=None, names=GFF_COLS, low_memory=False)
fasta = Fasta("data/reference_genomes/3-1_LsT2T.genome.fa", as_raw=True)   # as_raw=True 更快

genes = gff[gff.feature == "gene"].copy()        # 以实际GFF的命名为准
genes["gene_id"] = genes.attr.str.extract(r"ID=([^;]+)")
exons = gff[gff.feature == "exon"].copy()
exons["gene_id"] = exons.attr.str.extract(r"Parent=([^;]+)")  # Parent 可能指向 mRNA，需按实际文件再映射一层

def regions_of(g):
    """启动子: TSS上游2000bp（按链方向）；外显子: 该基因全部exon区间"""
    if g.strand == "+":
        prom = (g.chrom, max(g.start - 2000, 1), g.start, "+", "promoter")
    else:
        prom = (g.chrom, g.end, g.end + 2000, "-", "promoter")
    yield prom
    for _, e in exons[exons.gene_id == g.gene_id].iterrows():
        yield (e.chrom, e.start, e.end, g.strand, "exon")

PAM_FWD = re.compile(r"(?=([ACGT]GG))")   # 正链 NGG
PAM_REV = re.compile(r"(?=(CC[ACGT]))")   # 负链 CCN

def scan_region(chrom, start, end, strand, rtype, gene_id):
    seq = str(fasta[chrom][start-1:end]).upper()   # pyfaidx 是0-based含端点
    out = []
    for m in PAM_FWD.finditer(seq):                # 正链：NGG上游20nt
        if m.start() >= 20:
            g20 = seq[m.start()-20 : m.start()]
            out.append((gene_id, chrom, start+m.start()-20, start+m.start()+2,
                        "+", g20, seq[m.start():m.start()+3], rtype))
    for m in PAM_REV.finditer(seq):                # 负链：CCN下游20nt，取反互补
        s = m.start() + 3
        if s + 20 <= len(seq):
            g20 = str(Seq(seq[s : s+20]).reverse_complement())
            out.append((gene_id, chrom, start+m.start(), start+s+19,
                        "-", g20, str(Seq(seq[m.start():m.start()+3]).reverse_complement()), rtype))
    return out

rows = []
for _, g in genes.iterrows():
    for reg in regions_of(g):
        rows.extend(scan_region(*reg, g.gene_id))

cols = ["gene_id","chrom","start","end","strand","seq20","pam","region_type"]
cand = pd.DataFrame(rows, columns=cols).drop_duplicates(["chrom","start","end","strand"])

# 边界截断的 gRNA 取不出 30nt 上下文，丢弃
def get_seq30(r):
    # start/end 为 1-based 闭区间（seq20+PAM 共 23nt）；pyfaidx 切片为 0-based 半开
    if r.strand == "+":
        return str(fasta[r.chrom][r.start-5 : r.end+3]).upper()
    s = str(fasta[r.chrom][r.start-4 : r.end+4]).upper()
    return str(Seq(s).reverse_complement())   # 与01脚本逻辑一致：+链取[start-4,end+3]，-链取[start-3,end+4]再反互补
cand["seq30"] = cand.apply(get_seq30, axis=1)
cand = cand[cand.seq30.str.fullmatch(r"[ACGT]{30}")]
cand.insert(0, "guide_id", [f"Lsat_{i:06d}" for i in range(len(cand))])
cand.to_csv("results/grna_candidates_lettuce_0923.csv", index=False)
```

**时间安排**：
- 9.22 第 1–2 小时：GFF 解析 + regions_of；第 3 小时：在 1 条染色体上小跑验证（抽 10 个候选，用 genome browser 或手工核对坐标与序列）；
- 9.23 第 1–2 小时：全基因组跑（预计 10–60 分钟，若超过 2 小时：先只跑外显子区、promoter 砍到 1000bp，或按染色体并行 `multiprocessing.Pool`）；第 3 小时：统计产出（候选总数、每基因平均条数、promoter/exon 比例），写入 `results/scan_stats_0923.md`。
- 9.23 晚另安排约 1 小时（F3 收件后）：用 GFF 给生B 交来的 `nlr_genes_514.csv` 按 `gene_id` 批量回填坐标（`chr`、`start_bp`、`end_bp`、`strand` 四列），**9.24 前交回生B 抽查**；回填脚本顺手存 `scripts/` 备查。

**验收标准**：`results/grna_candidates_lettuce_0923.csv` 产出；每基因候选数分布合理（全为 0 或全 >500 都是 bug 信号）；抽 10 条手工核对通过。候选量级预期几十万到一百万条。

---

### B3 · 9.24（周四）Cas-OFFinder 脱靶预测

**部署（Windows）**：

```bash
# 从 GitHub Release 下载 Windows 版（sbgultom/cas-offinder 或原始 snyngki/cas-offinder 的 release 中有 win64 包）
# 解压得到 cas-offinder.exe，放到 cs_pipeline/tools/
# 准备染色体目录：Cas-OFFinder 要求 fasta 文件单独放在一个目录
mkdir -p data/lettuce/chrs && cp data/reference_genomes/3-1_LsT2T.genome.fa data/lettuce/chrs/
# 若基因组是多条 fasta 记录在一个文件，先用脚本拆成每条染色体一个 .fa（Cas-OFFinder 官方做法）
```

**输入文件格式（`data/lettuce/casoffinder_input.txt`）**：

```
<项目根>\cs_pipeline\data\lettuce\chrs
NNNNNNNNNNNNNNNNNNNNNNNGG
ACGTACGTACGTACGTACGT 3
```
（第 1 行：染色体 fasta 目录；第 2 行：20 个 N + PAM 模式；之后每行：一条候选 guide 序列 + 允许错配数。**错配数取 3**（2–3 区间取宽一档；需要更严口径时另看 mis2/mis1 列），DNA/RNA bulge 默认 0。）

```bash
tools/cas-offinder.exe data/lettuce/casoffinder_input.txt C results/offtarget_raw_0924.txt
# 第三个参数 C = CPU；有NVIDIA显卡可用 G（GPU快10倍以上）
```

**3 小时安排**：
- 第 1 小时：部署 + 用 5 条已知 guide 小规模试跑，确认输出格式（每行：guide、染色体、位置、方向、错配数、靶序列）；
- 第 2 小时：**性能现实检查**——全量几十万条 × 2.59Gb 在 CPU 上不可行。策略：先用计A 的 `predict.py` 给所有候选打分，**只取每基因 top 5**（约 4 万基因 × 5 ≈ 20 万条仍太多 → 再按 demo 演示范围收敛：报告/demo 实际只需展示 20–50 个代表基因，先对这 20–50 个基因的全部候选跑脱靶，全量留作"框架支持"）。⚠️ 这个取舍 9.24 中午前在群里确认，写进报告"方法与局限"；
- 第 3 小时：解析输出，统计每条 guide 的脱靶位点数（错配 ≤3），产出 `results/offtarget_counts_0924.csv`（列：guide_id、offtarget_count_mis3、offtarget_count_mis2、offtarget_count_mis1）。

**验收标准**：小规模试跑输出可解析；目标基因范围内每条候选 guide 都有脱靶计数；`casoffinder_input.txt` 与运行命令记入 `results/offtarget_runlog_0924.md`（可复现）。

---

### B4 · 9.25–9.26（周五、六）Streamlit demo

```bash
pip install streamlit
```

**页面结构（`app/app.py` 骨架，1–2 天出活，不做美化竞赛）**：

```python
import streamlit as st
import pandas as pd
import sys; sys.path.append("..")
from scripts.predict import predict_efficiency     # 计A 9.17 交付的接口

st.set_page_config(page_title="菊科菊苣族 gRNA 设计工具", layout="wide")
st.title("菊科（菊苣族）CRISPR/Cas9 gRNA 设计工具")
st.caption("DeepSpCas9 + CRISPRon Stacking 集成模型 · 莴苣 T2T 基因组演示")

# 预计算资源（启动时加载一次）
cand  = pd.read_csv("../results/grna_candidates_lettuce_0923.csv")
off   = pd.read_csv("../results/offtarget_counts_0924.csv")
cen   = pd.read_csv("../data/lettuce/centromere_regions.bed", sep="\t",
                    names=["chrom","cstart","cend"])

tab1, tab2 = st.tabs(["按基因名检索", "按自定义序列打分"])

with tab1:
    gene = st.text_input("输入基因 ID（如 lettuce_v2_00041910）")
    if gene:
        sub = cand[cand.gene_id == gene].copy()
        if sub.empty:
            st.warning("未找到该基因的候选 gRNA")
        else:
            sub["efficiency_score"] = predict_efficiency(sub.seq30.tolist())
            sub = sub.merge(off, on="guide_id", how="left")
            sub["in_centromere"] = sub.apply(
                lambda r: ((cen.chrom == r.chrom) &
                           (cen.cstart <= r.start) & (r.end <= cen.cend)).any(), axis=1)
            sub = sub.sort_values("efficiency_score", ascending=False)
            st.dataframe(sub[["guide_id","seq20","pam","region_type",
                              "efficiency_score","offtarget_count_mis3",
                              "in_centromere"]].head(20))
            st.download_button("下载全部候选(CSV)", sub.to_csv(index=False),
                               file_name=f"{gene}_grna.csv")

with tab2:
    seq = st.text_area("粘贴 30bp 序列（4nt上游+20nt guide+NGG+3nt下游），每行一条")
    if st.button("打分") and seq:
        seqs = [s.strip().upper() for s in seq.splitlines() if s.strip()]
        scores = predict_efficiency(seqs)
        st.dataframe(pd.DataFrame({"seq30": seqs, "efficiency_score": scores}))
```

```bash
cd /d <项目根>\cs_pipeline\app
streamlit run app.py        # 浏览器自动打开 http://localhost:8501
```

**时间安排**：
- 9.25 第 1 小时：接计A 的 `predict.py`，跑通"按自定义序列打分"页（不依赖基因组资源，先通这条）；第 2–3 小时：按基因名检索页 + 脱靶数/着丝粒标注合并；
- 9.26 第 1 小时：用 3 个真实基因端到端演示，截图存 `results/demo_screenshots_0926/`（视频录制 10.1 用）；第 2 小时：录屏走查一遍用户流程，修掉报错；第 3 小时：写 demo 使用说明（并入 README）。

**验收标准**：输入基因名 → 20 行内出排序表（含效率分、脱靶数、是否着丝粒区三列齐全）；自定义序列页对一条 30bp 序列返回分数；全流程无异常报错。demo 美不美观不作验收项。

---

### B5 · 10.2（周五）源码打包规范

**3 小时安排**：
- 第 1 小时：整理仓库，最终结构 = 0.4 节目录树；删除中间垃圾文件（临时 csv、调试 notebook）；
- 第 2 小时：写 `README.md`（模板见下）与 `requirements.txt`；
- 第 3 小时：在干净的 conda 环境里按 README 走一遍安装流程（换台机器或新建环境），确认可复现。

**`requirements.txt` 生成方式**（不要直接 `pip freeze` 全量倾倒，只列直接依赖）：

```
pandas>=2.0
scikit-learn>=1.3
biopython>=1.81
pyfaidx>=0.7
streamlit>=1.28
matplotlib>=3.7
joblib>=1.3
scipy>=1.11
```

（R 侧依赖在 README 中单独说明：`BiocManager::install("crisprScore")`，R≥4.3。）

**README.md 必须包含**：项目一句话简介、目录结构、环境搭建步骤（conda 命令逐条）、复现流程（从 hitom_clean_v1.csv 到 demo 的命令序列，按 scripts/ 编号顺序）、模型与指标摘要（引用 results/model_comparison_0919.csv 的数字）、外部工具说明（Cas-OFFinder 版本与下载地址）、数据说明（哪些数据未随代码发布及原因）。**README 全文不得出现校名、院系名、师生姓名**（详见 10.3）。

**验收标准**：干净环境下按 README 可完成环境搭建；`streamlit run app.py` 可启动（基因组大文件不随包发布，README 注明获取方式）；包内无任何含真实姓名/校名的字符串（用 10.3 的检查命令先自查一遍）。

---

## 3. 两人共同参与的三件事

### 3.1 9.12 D2 决策（各 1 小时并入当天安排）
计A 主讲 ρ 结果，计B 复核坐标/取向代码（第二双眼睛看 `01_build_seq30.py` 的 strand 分支——这是 ρ<0.2 时的头号嫌疑）。结论按 A2 分档表执行，写入 `results/transferability_D2_0912.md` 并发群里确认。

### 3.2 9.27 指标冻结（两人各 1 小时）
- 冻结清单（冻结后任何数字不得再改，报告/PPT/视频全部以这批为准）：
  - `results/transferability_D2_0912.md` 中的两个 ρ；
  - `results/model_comparison_0919.csv` 全部指标；
  - `results/logo_cv_0916.csv` 汇总值；
  - `results/scan_stats_0923.md`、`results/offtarget_runlog_0924.md` 中的规模数字；
  - 代码打 tag：`git tag v1.0-freeze`。
- 若当天发现某个数字要改：全队讨论后改，并在 `results/CHANGELOG_0927.md` 记录"改了什么、为什么"——评审问起来有据可查。

### 3.3 10.3 匿名化专项检查（两人各 1 小时，遗漏直接取消资格，务必逐条打勾）
计算机系负责的范围：**代码包、demo 录屏、PPT 中的代码截图**。

```bash
cd /d <项目根>
# 在代码包和文档中搜索身份信息（把示例词换成真实校名/姓名逐一查）
grep -ri --include="*.py" --include="*.R" --include="*.md" --include="*.txt" \
     --include="*.yml" -E "大学|学院|教授|老师|@.*\.edu" cs_pipeline/ | grep -v "BiocManager\|bioconductor\|github"
# 检查 git 历史与配置文件
cd cs_pipeline && git log --format='%an %ae' | sort -u   # 作者名不得含真实姓名
cat .git/config                                          # 不得含个人邮箱
```

检查清单：
- [ ] 所有源码/文档无校名、院系名、师生姓名、学号；
- [ ] git 提交者信息已匿名（如已污染：`git -c user.name="team" -c user.email="team@example.com" ...` 重建历史或干脆删除 `.git` 只交付快照）；
- [ ] 代码注释、文件路径（如 `C:\Users\真实姓名\...`）无个人信息——**重点查 Streamlit 截图和录屏里的终端路径、浏览器书签栏**；
- [ ] README、requirements.txt、environment.yml 无身份线索；
- [ ] demo 录屏中 localhost 页面、终端、文件名均已检查；
- [ ] 与生物系交叉确认：他们负责的报告/PPT/评审表同样过检。

---

## 4. 验收标准总表（什么叫做完）

| # | 交付物（精确路径） | 截止 | 验收标准 | 负责 |
|---|---|---|---|---|
| 1 | `cs_pipeline/env/environment.yml` | 9.9 | 新机器 `conda env create -f` 可建；示例序列打出 DeepSpCas9 分 | 计A |
| 2 | `cs_pipeline/data/hitom/hitom_seq30_0909.csv` | 9.9 | 行数=生物系交付数；seq30 长度=30 且通过 seq20/pam 一致性断言 | 计A |
| 3 | `cs_pipeline/results/scores_deepspcas9_0910.csv`、`scores_crispron_0911.csv` | 9.11 | 无 NA，行数与主表一致 | 计A |
| 4 | `cs_pipeline/results/transferability_D2_0912.md` | 9.12 | 含两模型 ρ/p 值、分档结论；结论可一键复现 | 计A+计B |
| 5 | `cs_pipeline/results/feature_matrix_0914.csv` | 9.14 | 无 NA、无常数列；特征相关性图已出 | 计A |
| 6 | `cs_pipeline/results/meta_model_ridge_0919.joblib` + `scripts/predict.py` | 9.17 | `predict_efficiency(seq30_list)` 接口可用，计B 试跑通过 | 计A |
| 7 | `cs_pipeline/results/model_comparison_0919.csv` + 散点图 | 9.19 | **测试集 ρ ≥ 0.5**（不达标则混合预案已执行并有记录）；单模型 vs 集成对比齐全 | 计A |
| 8 | `cs_pipeline/data/reference_genomes/3-1_LsT2T.genome.fa(.fai)` + GFF | 9.21 | pyfaidx 随机取区间与 samtools 结果一致 | 计B |
| 9 | `cs_pipeline/results/grna_candidates_lettuce_0923.csv` | 9.23 | 只覆盖基因区；每基因候选数分布合理；抽检 10 条坐标正确 | 计B |
| 10 | `cs_pipeline/results/offtarget_counts_0924.csv` + runlog | 9.24 | 目标基因范围全覆盖；错配≤3；命令可复现 | 计B |
| 11 | `cs_pipeline/app/app.py` + 截图 | 9.26 | 基因名→排序表（效率分+脱靶数+着丝粒标注）；自定义序列页可用 | 计B |
| 12 | 指标冻结 tag `v1.0-freeze` | 9.27 | 冻结清单全部归档 | 两人 |
| 13 | `cs_pipeline/README.md` + `requirements.txt` 打包 | 10.2 | 干净环境按 README 可复现安装与启动 | 计B |
| 14 | 匿名化检查清单全部打勾 | 10.3 | grep 检查零命中 | 两人 |

---

## 5. 与生物系接口清单（CS 等他们给什么）

| 文件 | 内容 | 生物系交付时间 | 列名/格式约定 |
|---|---|---|---|
| `hitom_clean_v1.csv` | 清洗后的橡胶草 Hi-TOM 统一表 | **9.9 晚 24:00**（D1 决策依赖它） | 见 0.4 节 12 列固定列名（含 `efficiency_norm`）；坐标已定稿 1-based 闭区间 |
| 橡胶草参考基因组 fasta | 补 30bp 上下文用 | 9.9 前 | fasta + 染色体命名与 hitom 表 `chrom` 列一致 |
| 莴苣 T2T 基因组 + GFF3 | 扫描对象 | 9.20–9.21（生物系浏览器下载 Figshare） | 放 `data/lettuce/` |
| `centromere_regions.bed` | 着丝粒区坐标（出自 T2T 论文补充表，本仓库已有 `T2T_Supplemental_Tables_7-9(1).xlsx` 可参考） | 9.23 晚（F3） | 三列：chrom、start、end，tab 分隔，无表头，1-based 闭区间（项目内部约定） |
| `nlr_genes_514.csv` | NLR 基因表（生B 整理、计B 用 GFF 回填坐标） | 9.23 晚收件（F3），9.24 前交回生B 抽查 | 列：gene_id、nlr_type、grey_mold_responsive、chr、start_bp、end_bp、strand |
| 批次归一化口径确认 | 哪些批次可合并、剔除标准 | 9.8 当面 | 归一化由生A 完成（产出 `efficiency_norm` 列），CS 只确认口径、不擅自决定剔除也不重算 |

CS 回传给生物系的（他们写报告/PPT 用）：9.12 的 D2 结论与散点图、9.14 特征相关性图、9.19 模型对比表与散点图、9.26 demo 截图。所有图默认 PNG、300dpi 等效、无身份信息。
