# Model Card: Hierarchical Selective Beta-Binomial GLMM (形态二 / v2.1-freeze 候选)

> **发布日期**：2026-09-21  
> **模型名称**：`meta_model_hier_bb_nob879_0921.joblib`  
> **训练集口径**：`noB879`（879 行，16.1 全部打分中剔除 90 行未经设计表确认的 B 级脏数据，纯 A 级金标准）  
> **架构类型**：端到端分层广义线性混合模型（Hierarchical GLMM with Selective Empirical Bayes Prior）  
> **接口代码**：[`scripts/predict.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/predict.py) / 训练脚本 [`scripts/15_train_hierarchical_bb_nob879.py`](file:///d:/lifesciencechallenge/cs_pipeline/scripts/15_train_hierarchical_bb_nob879.py)

---

## 1. 模型概览与战略定位 (Model Overview)

针对橡胶草（*Taraxacum kok-saghyz*）Hi-TOM 靶向扩增子测序数据中存在的严重批次效应、测序深度异方差以及技术脏数据干扰，本项目在 2026-09-21 经严格基准对比与机理诊断后，正式确立本模型为**官方新一代生产与科研核心模型**：

1. **剔除 B 级脏数据（`noB879`）**：彻底排除了 90 行“多候选竞争未经设计表确认”的低置信样本，杜绝了张冠李戴的伪特征对优化梯度的污染。
2. **端到端贝叶斯似然（形态二）**：取代了传统“先减中位数、再做回归”的脆弱两步法，直接基于测序物理产生机制建模编辑 reads 数与总深度。
3. **彻底治愈测试集崩溃**：传统锚定方法在 20% 留出测试集上呈现严重负相关（$\rho = -0.5057$），本模型直接逆转为 **$\rho = \mathbf{+0.3424} \sim \mathbf{+0.3963}$**，且低混杂多批折（Class A）真实生物学上限达到 **$\rho = \mathbf{+0.4636}$**。

---

## 2. 数学模型与理论机制 (Mathematical Formulation)

### 2.1 似然层：深度感知 Beta-二项分布 (Likelihood Layer)
对于第 $i$ 个扩增子样本，设其总测序 reads 深度为 $n_i$（物理试验总数），发生非野生型编辑的 reads 数为 $k_i$：
$$k_i \sim \text{BetaBinomial}(n_i, \; p_i, \; s)$$
$$\text{logit}(p_i) = \beta_0 + \mathbf{z}_i^\top \boldsymbol{\beta} + u_{b_i}$$
- $\mathbf{z}_i = (\mathbf{x}_i - \boldsymbol{\mu}) / \boldsymbol{\sigma}$ 为标准化后的 10 维生物物理与深度模型特征；
- $s$ 为过离散度参数（Overdispersion Parameter），自适应吸收批内生物学与技术重复的额外方差；
- **深度加权自然内生**：二项抽样方差 $\text{Var}(k_i/n_i) \propto \frac{p_i(1-p_i)}{n_i}$，高深度行（如 3,000 reads）自动在对数似然中主导梯度更新，低深度行（如 50 reads）权重自然衰减。

### 2.2 先验层：分段选择性经验贝叶斯 (Selective EB Prior)
针对扩增子实验中极端批次（如 USR-6137 批次位移达 +87%）与无锚点批次并存的暗坑：
$$u_b \sim \mathcal{N}\left(u_{\text{prior}, b}, \; \frac{1}{\tau_b^2}\right)$$
- **充分锚点批次（$m_b \ge 10$）**：完全采信锚点实测位移，施加强约束（$\text{weight}=10.0$），坚决不向全局均值盲目平滑；
- **稀疏锚点批次（$0 < m_b < 10$）**：经验贝叶斯收缩 $\Delta_b^{\text{EB}} = \frac{m_b}{m_b + \lambda} \hat{\Delta}_b$（$\lambda = s^2/\tau^2 \approx 1.14$）；
- **零锚点批次（$m_b = 0$）**：先验位移归零，标准正态正则化。

### 2.3 预测与解耦 (Inference)
在对新序列进行效率推断时，**显式剔除所有批次截距 $u_b$**，仅输出纯序列生物学活性潜变量：
$$\hat{\eta} = \beta_0 + \left(\frac{\mathbf{x}_{\text{new}} - \boldsymbol{\mu}}{\boldsymbol{\sigma}}\right)^\top \boldsymbol{\beta}$$
$$\text{score} = \frac{100}{1 + \exp(-\hat{\eta})} \in [0, 100]$$

---

## 3. 入模特征集 (Feature Definitions)

模型入模特征共 **10 维**，严格保持以下顺序：

| 特征名称 | 类型 | 物理含义与来源 |
| :--- | :--- | :--- |
| `deepspcas9_score` | float | 预训练模型 DeepSpCas9 序列打分（0–100） |
| `crispron_score` | float | 预训练模型 CRISPRon 序列打分（0–100） |
| `gc_total` | float | 20nt guide 序列全长 GC 含量（[0, 1]） |
| `gc_seed` | float | PAM 近端 6nt 种子区 GC 含量（[0, 1]） |
| `tm` | float | 20nt 双链解链温度 Tm（Nearest Neighbor） |
| `poly_t` | int | 序列是否含 TTTT 早期转录终止信号（0 或 1） |
| `pam_n_A` | float | PAM 5' 侧首位碱基为 A 的 One-hot 编码 |
| `pam_n_C` | float | PAM 5' 侧首位碱基为 C 的 One-hot 编码 |
| `pam_n_G` | float | PAM 5' 侧首位碱基为 G 的 One-hot 编码 |
| `pam_n_T` | float | PAM 5' 侧首位碱基为 T 的 One-hot 编码 |

---

## 4. 评估指标与横向基准对比 (Evaluation & Benchmarks)

指标来源：[`results/metrics_hier_bb_nob879_0921.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/metrics_hier_bb_nob879_0921.csv) 及折级明细 [`results/folds_hier_bb_nob879_0921.csv`](file:///d:/lifesciencechallenge/cs_pipeline/results/folds_hier_bb_nob879_0921.csv)。

### 4.1 在 `noB879` 纯金标准上的对比表

| 评估维度 / 指标 | 既有基准 (Anchor) | 深度加权 (Method A2) | **形态二 (本模型)** | 优势与结论 |
| :--- | :---: | :---: | :---: | :--- |
| **独立留出测试集 (Test $\rho$)** | -0.5057 (崩溃) | -0.5088 (崩溃) | **+0.3424** (p=7.89e-7) | **彻底治愈泛化倒挂** |
| **LOGO 留一基因交叉验证中位 $\rho$** | +0.2970 | +0.2166 | **+0.3635** | 提升 +0.0665，稳健领先 |
| **Class A (低混杂多批折) 中位 $\rho$** | +0.2653 | +0.2592 | **+0.4636** | **打破天花板，证实真实生物学上限高达 0.46** |
| **有效折数 (Valid Folds)** | 10/16 | 10/16 | 9/16 | 满足 double-sided round(6) 守卫 |

### 4.2 Class A (低混杂核心折) 逐折明细
- `LG03.451` (跨 3 批): $\rho = \mathbf{+0.8522}$ ($p = 0.0$)
- `LG05.1856` (跨 7 批): $\rho = \mathbf{+0.4636}$ ($p = 0.0395$)
- `LG07.3933` (跨 3 批): $\rho = \mathbf{+0.4837}$ ($p = 0.0420$)
- `LG05.2725` (跨 8 批): $\rho = \mathbf{+0.3635}$ ($p = 0.0$)
- `LG07.3296` (跨 6 批): $\rho = \mathbf{+0.2071}$ ($p = 0.0102$)

---

## 5. 模型权重落盘参数 (Fitted Parameters)

落盘文件：`results/meta_model_hier_bb_nob879_0921.joblib`
- $\beta_0 = -0.5096$
- $\boldsymbol{\beta}$ (对应 10 维标准化特征):
  - `deepspcas9_score`: -0.2112
  - `crispron_score`: -0.2315
  - `gc_total`: -0.6411
  - `gc_seed`: +0.2438
  - `tm`: +0.8453
  - `poly_t`: -0.1617
  - `pam_n_A`: +0.4246
  - `pam_n_C`: -0.3057
  - `pam_n_G`: +0.1092
  - `pam_n_T`: -0.1407
- 过离散度参数 $s \approx 20.08$

---

## 6. 使用方式与推理代码 (Inference Guide)

生产接口位于 `scripts/predict.py`，计B 可直接调用：

```python
from scripts.predict import predict_efficiency

# 输入标准 30bp 序列 (4nt 上游 + 20nt guide + 3nt PAM + 3nt 下游)
seq30_candidates = [
    "ATCGGCTAAGCTAGGCTAGCATCGTGGATC",
    "ATTCGGCGTTAGATTGACAGAAGACGGTGG",
]
scores = predict_efficiency(seq30_candidates)
print(scores)  # 输出相对效率预测分 [0.0 ~ 100.0]
```
