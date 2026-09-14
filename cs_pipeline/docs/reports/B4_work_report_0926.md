# 计B 组 9.26 日工作报告（B4 第二天：端到端演示 + 截图 + 走查）

> 执行时间：2026-09-11 傍晚 · 对应《分工详案_计算机系》（docs/plans/division_plan_cs.md）B4 节 9.26 安排
> 项目目录：`D:\lifesciencechallenge\cs_pipeline\` · git commit `b95bc8a`

---

## 一、结论速览

| 9.26 任务（详案 B4） | 状态 | 说明 |
|---|---|---|
| 3 个真实基因端到端演示 + 截图 | ✅ 完成 | 7 张截图存 `results/demo_screenshots_0926/`（真实浏览器驱动，非模拟） |
| 用户流程走查 + 修报错 | ✅ 完成 | 服务日志零异常；走查发现 3 个问题，均已处理（见下） |
| demo 使用说明并入 README | ✅ 完成（复核确认） | README "Streamlit demo（B4）" 节在（第 39–43 行），`docs/demo_使用说明_0925.md` 在 |

**验收对照（详案 #11）**：输入基因名 → 排序表（效率分 + 脱靶数 + 着丝粒标注齐全）✅；自定义序列页对 30bp 序列返回分数 ✅；全流程无异常报错 ✅。**9.25–9.26（B4）整段收工。**

---

## 二、具体做了什么

### 1. 三基因端到端演示（真实浏览器，in-app browser 驱动）
临时起服 `streamlit run app/app.py`（8599 端口，用完已停，无残留进程），依次演示：

| 基因 | 染色体 | 演示内容 | 截图 |
|---|---|---|---|
| LsaT2T01G023690 | Chr01 | 默认加载页 + 候选表 | `tab1_gene1_LsaT2T01G023690.png`、`tab1_gene1_table.png` |
| LsaT2T04G000980 | Chr04（− 链） | 基因切换 + 指标面板（坐标 4,541,850–4,547,566） | `tab1_gene2_*.png` |
| LsaT2T09G034950 | Chr09 | 候选表（383 条候选、查询耗时 **4 ms**，远低于 5s 要求）+ CSV 下载 | `tab1_gene3_*.png` |

Tab2 自定义序列：输入 2 条 30bp → 子进程调 crispr 环境 DeepSpCas9 实测打分，**24.1s 出结果**（71.2494 / 46.2756），附 CSV 下载 → `tab2_custom_scoring.png`。

### 2. 走查发现与处理（3 项）
1. **textarea 需 Ctrl+Enter 生效**（Streamlit 原生行为，直接点"打分"会提示"请先输入序列"）→ 在 Tab2 提示文案中补了操作提示；
2. **文案过时**："待实验数据交付后接入" —— 数据实际已于 9.11 交付 → 更新为"模型训练中（9.13–9.19）"（页头 caption + Tab2 提示 + 模块 docstring 共 3 处）；
3. 服务日志 grep 零 error/traceback；改动后 AppTest 复验无异常。

### 3. 清理与提交
- 发现并清理了一个**早前会话残留的 streamlit 进程**（PID 40016 占用 8501）；
- 浏览器标签页已关闭，demo 服务已停（healthz 确认无响应、无 streamlit 进程残留）；
- commit `b95bc8a`：7 张截图 + app.py 文案修改。`data/mini_*.txt` 等他人中间产物仍未入库（沿用昨日建议，待全队确认后加 .gitignore）。

## 三、需要实验数据而没做的

| 阻塞项 | 需要谁给 | 影响 |
|---|---|---|
| 真实效率分（Stacking 集成模型）进 demo | 计A 9.13–9.19 训练（数据 9.11 已交付，无阻塞） | demo 已预留 `predict_efficiency` 接口，模型一到即替换，**不影响 10.1 录屏** |

## 四、后续衔接
- 10.1 视频录制可直接复用今天的走查路线（3 基因 + 自定义序列）；
- 9.25 报告遗留建议：把 `data/mini_*.txt`、`results/off_mini_*.txt` 加入 .gitignore（待全队确认）。
