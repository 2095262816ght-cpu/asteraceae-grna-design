# Streamlit demo 使用说明（B4 · 0925）

## 启动

```bash
cd cs_pipeline
conda run -n grna-demo streamlit run app/app.py
# 或先 conda activate grna-demo，再 streamlit run app/app.py
```

浏览器打开终端输出的 Local URL（默认 <http://localhost:8501>）。

demo 运行于独立的 `grna-demo` 环境（`env/environment_demo.yml`）：genet 锁定
tensorflow<2.10 → protobuf<3.20，与 streamlit 冲突，因此打分不与应用同进程，
而是通过子进程调用打分环境（含 genet + DeepSpCas9 权重，可离线运行）执行
`app/score_deepspcas9_cli.py`，经 stdin/stdout 传序列与结果。

## 页面功能

### Tab 1 · 按基因名检索

- 下拉框选择基因（可输入关键字过滤），范围为 **49 个 NLR 代表基因**
  （demo 收敛策略，见 B3 runlog）。
- 过滤控件：着丝粒区 guide 过滤（默认开）、区域类型（promoter / exon）、
  排序依据（脱靶 mis3 升序 / 效率分降序 / GC% 接近 50%）。
- 基因信息面板：染色体、坐标、链、NLR 类型、过滤后候选数。
- 候选表：guide_id、seq20、pam、坐标、链、region_type、GC%、Tm、
  **效率分（占位）**、脱靶 mis1/2/3、完全匹配数、是否着丝粒区。
  展示 Top 10，可展开全部，并可一键下载当前过滤结果为 CSV。

### Tab 2 · 按自定义序列打分

- 文本框粘贴 30bp 序列，每行一条，布局为
  **4nt 上游 + 20nt guide + NGG PAM + 3nt 下游**。
- 前端校验：长度 = 30、仅含 A/C/G/T、第 25–27 位为 NGG；非法序列逐条报错，
  合法序列照常打分。
- 点击「打分」后子进程调 DeepSpCas9 模型（约十几秒，超时上限 120 s），
  结果以表格展示并可下载 CSV。

## 数据来源

| 文件 | 内容 |
| --- | --- |
| `demo/app_data.csv` | 19,839 条候选 gRNA（坐标、序列、GC/Tm、占位效率分、脱靶计数、着丝粒标注） |
| `demo/app_genes.csv` | 49 个 NLR 代表基因（坐标、链、NLR 类型） |

脱靶计数列部分为空（B3 跑批未完成部分）；着丝粒标注来自基因组着丝粒区间。

## 效率分现状（重要 · 9.13 更新）

- **Tab 1 的「效率分（Stacking预测）」已接入，但当前不可信**：`demo/app_data.csv`
  的 `efficiency_score`（19,839 条全量）由 `scripts/predict.py` 的
  `predict_efficiency` 产出，而该元模型在测试集上 ρ=-0.3435、AUC=0.3672
  （低于随机），且其 `crispron_score` 输入在 `predict.py` 内是人工线性式而非
  真实 CRISPRon 输出。**对外演示建议回退到 `efficiency_placeholder`
  （GC/Tm 序列启发式占位分）并明确标注为占位，或在页面上加免责说明。**
  详见 `results/CHANGELOG_0927.md` 的 9.13 更正记录。
- **Tab 2 的 DeepSpCas9 分为真实离线推理**（genet 0.17.2），可正常演示；
  同页的 Stacking 集成分受上述限制，不应作为效率结论解读。
- 原「`scripts/predict.py` 为接口占位（NotImplementedError）」的说明已过期：
  接口已于 9-12 实现并由计B 接通，问题不在链路连通，而在模型指标与特征来源。

## 常见问题

- 打分报错「找不到打分环境的 Python 解释器」：打分环境未安装或路径变更，
  可用环境变量 `CRISPR_PYTHON` 指向含 genet 的 python 后重启 demo。
- 打分超时（>120 s）：减少单次序列条数后重试。
