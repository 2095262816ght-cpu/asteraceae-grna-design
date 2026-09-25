# ADR 0002: 建立候选 gRNA 推荐与多组学决策引擎 (CandidateRankingEngine)

## 状态
Accepted

## 背景与上下文
在 `app/app.py` 的 Tab 1（候选 gRNA 检索与推荐）中，视图组件同时承担了大量业务决策与数据工程职责：
1. 分别加载 `app_data.csv`、`app_data_tissue_priority.csv`、`offtarget_functional_hazard_0923.csv` 并在内存中进行多表左连接；
2. 维护 4 级模型历史效率列的名称回退逻辑（`efficiency_score_v21_nob879` -> `efficiency_score_full_0916` -> `efficiency_score` -> `efficiency_placeholder`）；
3. 直接执行着丝粒布尔取反、区域类型过滤切片；
4. 实现多分支排序调度：组织优先指数降序、纯效率分降序、脱靶 mis3 升序、GC 偏差绝对值升序；
5. 将 `expression_status` 枚举字典映射为中文业务展示文本；
6. 逐列重命名以生成表格展示视图。

这种模式导致核心决策逻辑无法在离线环境、批处理分析或轻量单元测试中复用。任何排序公式调整都必须通过 Streamlit 前端来验证。

## 架构决议
1. 建立深度模块 `cs_pipeline/app/recommendation_engine.py`（类名 `CandidateRankingEngine`）。
2. 提供单一深度接口：
   ```python
   engine = CandidateRankingEngine.load_default(base_dir)
   result = engine.rank_candidates(
       gene_id: str,
       target_tissue: str,
       sort_by: str,
       region_types: list[str],
       hide_centromere: bool = True
   ) -> RankingView
   ```
3. 引擎内部管理：
   - 资产加载与缓存（候选库、多组学优先指数、功能性脱靶危害表）；
   - 模型历史版本列自动探测与元数据标签归一化；
   - 候选过滤规则与 GC 距离衍生；
   - 动态排序策略分发与稳定性保证；
   - 证据标签映射与表格展示列生成。
4. `app/app.py` 的 Tab 1 降解为纯渲染管道，仅向引擎传递用户交互参数并渲染返回的 `RankingView`。

## 收益与验证
- **Leverage**：调用方仅需传递意图参数，即可得到完整的 Top 10、全量视图、基因统计元数据及耗时；
- **Locality**：多组学业务逻辑集中于 `CandidateRankingEngine`，修改排序策略或列名映射无需修改 UI 控件；
- **Test Surface**：为 Tab 1 核心业务提供了纯 Python 内存单测能力，验证 9 条路径不再受限于 Streamlit 运行上下文。
