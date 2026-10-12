# 计B 组 9.25 日工作报告（B4 第一天：Streamlit demo）

> 执行时间：2026-09-11 午 · 对应《分工详案_计算机系》（docs/plans/division_plan_cs.md）B4 节 9.25 安排
> 项目目录：`<项目根>\cs_pipeline\` · git commit `7a86d34`

---

## 一、结论速览

| 9.25 任务（详案 B4） | 状态 | 说明 |
|---|---|---|
| 建 demo 专用环境 `grna-demo` | ✅ 完成 | streamlit 1.63.0 + pandas 2.3.3（与 crispr 环境隔离，规避 protobuf 冲突） |
| Tab2「按自定义序列打分」跑通 | ✅ 完成 | 不依赖基因组资源，优先打通（符合详案第 1 小时安排） |
| Tab1「按基因名检索」+ 脱靶数/着丝粒标注合并 | ✅ 完成 | 基于 demo/app_data.csv（49 个 NLR 基因、19,839 条候选） |
| 接入计A `predict.py`（Stacking 效率分） | ⚠️ **未接入——等实验数据** | `scripts/predict.py` 仍是 NotImplementedError 占位；计A 集成模型训练依赖生物系 `hitom_clean_v1.csv`（未交付）。页面已用占位启发式分并明确标注 |
| demo 使用说明 | ✅ 完成 | `docs/demo_使用说明_0925.md` + README 复现流程更新 |

**验收对照（详案 #11 中 9.25 部分）**：自定义序列页对 30bp 序列返回分数 ✅；基因名 → 排序表（效率分 + 脱靶数 + 着丝粒标注三列齐全）✅；全流程无异常报错 ✅。

---

## 二、具体做了什么

### 1. 环境 `grna-demo`
- `conda env create -f env/environment_demo.yml` 一次建成（清华镜像，未触发代理）。
- 独立环境的原因（沿用 9.8 定型结论）：genet 锁 protobuf<3.20，与 streamlit>=1.63 硬冲突，不能共存于 crispr 环境；demo 侧打分通过**子进程**调 crispr 环境的 Python 完成。

### 2. `app/app.py` 两页完整版（重写骨架）
- **Tab1 按基因名检索**：selectbox 选基因（可输入过滤）；着丝粒区过滤、region_type 筛选、多排序依据；结果表含 seq20/pam/region_type/**效率分（占位）**/**offtarget_count_mis3**/**in_centromere** 等 16 列；Top-N + 全部候选展开 + CSV 下载按钮。复用了 `demo/app.py`（旧单页版）的过滤/展示逻辑。
- **Tab2 按自定义序列打分**：textarea 每行一条 30bp，前端校验（长度=30、仅 ACGT、25–27 位 NGG，非法逐条报错）；子进程调 `app/score_deepspcas9_cli.py`（stdin 进、CSV 出）跑 genet DeepSpCas9，120s 超时与错误展示。页面明确注明：当前为 DeepSpCas9 单模型分，Stacking 集成模型待计A数据到位后经 `predict_efficiency` 接口接入。

### 3. 端到端验证（全部通过后已关停服务，无残留进程）
- AppTest 无头执行两页均无异常；Tab2 实测：`ATCGGCTAAGCTAGGCTAGCATCGTGGATC → 71.2494`（与基准 71.25 吻合）、`TTTGTGGATTCCGGTAGAATCTGATGGAAT → 46.2756`（2 条约 13s）。
- 服务级：`streamlit run app/app.py` 起服后 HTTP 200（/healthz 200），日志无 traceback。
- 匿名红线：grep 确认页面与文档无校名/人名/本机用户路径（crispr python 路径走代码常量，可用 `CRISPR_PYTHON` 环境变量覆盖）。

### 4. 顺手处理的问题
- streamlit 1.63 的 `use_container_width` 弃用警告 → 改 `width="stretch"`，复测无警告。
- `git add -A` 发现会带入 132MB 他人批处理中间产物（`data/mini_*.txt`、`results/off_mini_*.txt`）→ 已 unstage 未入库；**建议**后续把这两个 pattern 加进 .gitignore（本次未擅改他人文件）。

## 三、需要实验数据而没做的（阻塞项）

| 阻塞项 | 需要谁给 | 影响 |
|---|---|---|
| Tab1/Tab2 的**真实效率分**（Stacking 集成模型） | 生物系 `hitom_clean_v1.csv` + 橡胶草参考基因组（原定 9.8 晚交付，至今未到）→ 计A 才能训练模型并在 9.17 实现 `predict.py` | 目前两页的效率分分别是：Tab1 序列启发式占位分（GC/Tm）、Tab2 DeepSpCas9 单模型分。页面均有显著标注，**demo 框架本身已完备**，模型一到只需替换打分来源，不影响 9.26 的端到端演示与截图 |

## 四、次日（9.26）待办衔接
- 用 3 个真实基因端到端演示并截图存 `results/demo_screenshots_0926/`（服务已验证可起，截图待做）；
- 录屏走查用户流程、修报错；demo 说明已备好（`docs/demo_使用说明_0925.md`）。
