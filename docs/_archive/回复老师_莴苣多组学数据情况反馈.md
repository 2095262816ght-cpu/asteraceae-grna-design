# 关于项目数据情况与方案调整的回复

老师您好，您的两条消息我们都收到了，逐一核实、讨论后整理如下：

## 一、两物种数据现状总表

| 数据类型 | 莴苣（模式物种） | 橡胶草（目标物种） |
|---|---|---|
| 参考基因组 + 注释 | ✅ 公开可得（LettuceGDB，Salinas_v8 等） | ✅ 老师/实验室可提供 |
| RNA-seq | ✅ 公开可得 | ✅ 老师/实验室可提供 |
| ATAC-seq | ⚠️ LettuceGDB 有数据，BED 文件待联系作者（老师已在联系） | ❌ 没有 |
| ChIP-seq | ❌ 没有 | ❌ 没有 |
| gRNA 活性训练标签 | ❌ 没有 → **用现有工具预测分做"伪标签"**（老师的建议，详见第二节） | ✅ 可收集少量真实标签（老师与师弟师妹们整理中） |

## 二、对老师"伪标签"建议的回应：完全可行，且与我们的方案高度契合

老师提到的"20 余种植物 gRNA 效率预测工具评估、多个机器学习模型与实验编辑效率 Spearman 相关 > 0.8"的结论非常关键，我们完全认同，理由有三：

1. **已读文献直接支持这一策略**。我们精读的 Chen2022（Bioinformatics）系统评估了 15 个主流算法，发现顶级模型（CRISPRon、DeepSpCas9、DeepHF）在独立数据集上表现稳定，且其 Stacking 集成模型（ensemble_ridge）优于任何单一算法。这正好给老师说的"多个工具的预测结果"提供了一个标准用法：**不用单一工具的分数做伪标签，而是把多个高相关工具的分数做集成（Stacking + 岭回归），得到更稳健的伪标签**。
2. **与我们已定的执行大纲不谋而合**。我们的《迁移学习项目执行大纲》第 4 步本就写了"伪标注：预训练模型给候选 gRNA 批量打分，伪标注数据预训练 + 真实数据微调"这一条扩充途径。老师的建议相当于把它从"备用扩充手段"提升为"莴苣侧的主线策略"，我们评估这在科学上站得住。
3. **橡胶草的少量真实标签恰好补上了伪标签策略最大的短板**——可信度验证。具体用法（见第三节）：
   - 若标签只有几条到几十条：**不做训练**，专门用作"金标准"验证集，检验伪标签模型和迁移模型在橡胶草上的 Spearman 相关性——这是答辩时最有说服力的证据；
   - 若最终能收集到上百条：可再做一轮小样本校准/微调（按大纲决策点：<100 条走 Stacking 元模型，≥几百条才走神经网络微调）。

**一个需要在报告中说明的科学细节**：Spearman > 0.8 是这些工具在"已有植物实验数据"上的相关性，伪标签迁移到菊科新物种时必然有偏倚。所以我们项目的核心卖点就定为——**"伪标签预训练 + 真实标签验证校准"的跨物种策略**，用橡胶草的真实数据定量评估伪标签策略的有效性边界。这本身就是对老师提到的那篇评估研究的延伸和落地。

## 三、根据现有数据调整后的 20 天方案

综合两条消息，方案做如下调整（核心变化：**橡胶草侧放弃表观特征，莴苣侧标签改走伪标签路线**）：

**总体思路**：莴苣侧用"序列 + ATAC-seq + RNA-seq"特征 + 伪标签训练多组学效率模型 → 通过同源映射迁移到橡胶草 → 用橡胶草真实标签验证校准 → 封装成在线工具。竞赛主题（赛道二：AI 基因编辑与核酸工具设计）完全吻合。

| 阶段 | 时间 | 内容 |
|---|---|---|
| 第 1 阶段：数据与基线 | 第 1–5 天 | ① 下载莴苣基因组/注释/RNA-seq；② 橡胶草基因组、RNA-seq 数据入库；③ 跑通 3–4 个顶级预测工具（DeepSpCas9、CRISPRon 等），在两物种基因组上批量扫描 NGG PAM 靶点并打分，构建伪标签数据集；④ 等老师 ATAC-seq 联系结果，拿不到就用 LettuceGDB 原始数据自行 MACS2 call peak（备用路径，约 1–2 天） |
| 第 2 阶段：莴苣核心模型 | 第 6–11 天 | ① 特征工程：序列特征 + ATAC 开放染色质特征 + 基因表达特征 + 区域注释特征（启动子/外显子，用 TSS 注释 + ATAC 交集替代 ChIP-seq）；② 多工具分数 Stacking 集成生成稳健伪标签；③ 训练莴苣多组学效率模型，并与"纯序列基线模型"对比，量化多组学特征的增益（这是报告的核心结果之一） |
| 第 3 阶段：跨物种迁移与验证 | 第 12–16 天 | ① 同源映射：橡胶草基因 ↔ 莴苣基因比对，迁移效率评分与特征权重；② **用橡胶草真实标签做独立验证**：计算迁移预测 vs 实测效率的 Spearman 相关，出散点图和相关性报告（答辩亮点）；③ 若标签数量允许，做一轮校准微调并报告提升幅度 |
| 第 4 阶段：工具封装与交付 | 第 17–20 天 | ① 简化版在线工具：输入基因/序列 → 输出 gRNA 列表 + 效率评分 + 脱靶提示（脱靶集成 Cas-OFFinder 规则版即可，不做全基因组索引以省时间）；② 整理报告书、PPT、讲解视频、源码（注意匿名化要求） |

**20 天可行性评估**：可行，且留了缓冲——第 4 阶段的网页封装若紧张，可先做成"命令行脚本 + 本地演示页面"，把工作量压在算法验证这个得分点上；ATAC-seq 若两条路径都不通，最坏情况下退化为"序列 + 表达"特征模型，方案主体不受影响。

## 四、莴苣 ATAC-seq 数据：已核实的详细信息（供老师联系作者时参考）

我们实际访问了 https://lettucegdb.com/atacseq，情况如下：

1. **页面可以正常打开**，该模块是"ATAC-seq 显著 peak 检索系统"，但需先输入基因 ID 检索才显示结果（直接打开显示 0 results）。
2. 该模块基于的参考基因组版本是 **Stem lettuce genome v1.1c**，页面提供原始数据下载入口（lettucegdb.com/data/ATAC-Seq/）。
3. 旁证：Cao 等人 2024 年 Genome Biology 的生菜驯化 DNA 甲基化论文（我们已精读），其方法就是直接从 LettuceGDB 下载 ATAC-seq 原始数据自行分析的——**原始数据确认公开可得**。

**建议老师联系作者时明确 4 点**（可提高成功率）：

1. **索要内容**：ATAC-seq peak 的 BED/narrowPeak 文件，最好含 peak 注释（邻近基因、启动子/外显子/内含子类型）和信号强度（如 -log10(q-value)）；
2. **基因组版本**：确认 BED 坐标基于哪个参考基因组版本（v1.1c 还是 Salinas_v8），并请提供对应基因组文件或 liftOver 链文件——LettuceGDB 页面基于 v1.1c，而多数论文数据基于 Salinas_v8，版本不统一坐标就无法对齐，这是我们最担心的技术点；
3. **用途说明**：本科生竞赛项目（第一届全球大学生生命科学挑战赛），仅学术研究、非商业用途，成果中注明来源并引用其论文；
4. **兜底请求**：若不便分享处理后的 BED，退而求其次请作者提供 peak calling 参数（MACS2 设置等），我们从公开原始数据自行复现。

**ChIP-seq 缺失已有成熟替代方案，不影响项目**：用基因注释 TSS 上游 1–2 kb 定义启动子 + RNA-seq 表达量区分基因活性 + ATAC-seq peak 与启动子取交集得到"开放启动子"，这是植物 ATAC-seq 研究的标准做法。

## 五、需要老师这边协助的事项汇总

1. 联系 LettuceGDB 作者索要 ATAC-seq BED 文件（要点见第四节，邮件模板见附录）；
2. 收集橡胶草 gRNA 活性标签时，烦请尽量保留每条标签的：gRNA 序列、基因组坐标（或靶向基因）、PAM、实测效率值、实验批次——坐标和批次信息对后续分析很重要；
3. 橡胶草基因组和 RNA-seq 数据准备好后，告知我们数据格式和获取方式即可。

---

## 附：联系 LettuceGDB 作者的英文邮件模板（供老师参考）

> Dear Dr. [姓名],
>
> I am [老师姓名], a faculty member at [学校]. My undergraduate students are participating in the Global Undergraduate Life Science Challenge, developing a CRISPR gRNA design tool for Asteraceae plants based on multi-omics data from lettuce.
>
> We noticed the ATAC-seq module on LettuceGDB (lettucegdb.com/atacseq) and your related publications. Our project only requires the **processed peak files in BED/narrowPeak format** (chromosome, start, end, associated gene, region annotation, and signal value) — not the raw sequencing data.
>
> Would it be possible to share these peak files with us? We would also appreciate knowing which reference genome version the coordinates are based on (Stem lettuce v1.1c or Salinas_v8). The data will be used strictly for non-commercial academic research, and your work will be properly credited and cited in our project.
>
> If sharing the processed files is inconvenient, we would be grateful for the peak-calling parameters (e.g., MACS2 settings) so we can reproduce them from the publicly available raw data.
>
> Thank you very much for your time and for maintaining such a valuable community resource.
>
> Best regards,
> [署名]
