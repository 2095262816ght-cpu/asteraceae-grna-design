# Hi-TOM: a platform for high-throughput tracking of mutations induced by CRISPR/Cas systems

> **抄写版说明**：本文正式版由 Springer（Science China Life Sciences）出版，属于付费墙内容，直接下载 PDF 返回的是 HTML 验证页；Sciengine 镜像返回 418；该文未收录于 PMC（无开放获取全文）。因此按约定改为抄写版，以下信息来自 PubMed 官方记录（PMID 30446870）。

## 文献信息

- **标题**：Hi-TOM: a platform for high-throughput tracking of mutations induced by CRISPR/Cas systems
- **作者**：Liu Q, Wang C, Jiao X, Zhang H, Song L, Li Y, Gao C, Wang K（第一作者：Qi Liu 刘琦；通讯作者：Kejian Wang 王克剑）
- **单位**：中国水稻研究所 水稻生物学国家重点实验室（杭州）；中国科学院遗传与发育生物学研究所；上海交通大学医学院上海儿童医学中心等
- **期刊**：Science China Life Sciences
- **年份**：2019（2019 Jan; 62(1):1-7；2018-11-13 在线发表）
- **DOI**：10.1007/s11427-018-9402-9
- **PMID**：30446870

## 摘要全文

The CRISPR/Cas system has been extensively applied to make precise genetic modifications in various organisms. Despite its importance and widespread use, large-scale mutation screening remains time-consuming, labour-intensive and costly. Here, we developed Hi-TOM (available at www.hi-tom.net/hi-tom/), an online tool to track the mutations with precise percentage for multiple samples and multiple target sites. We also described a corresponding next-generation sequencing (NGS) library construction strategy by fixing the bridge sequences and barcoding primers. Analysis of the samples from rice, hexaploid wheat and human cells reveals that the Hi-TOM tool has high reliability and sensitivity in tracking various mutations, especially complex chimeric mutations frequently induced by genome editing. Hi-TOM does not require special design of barcode primers, cumbersome parameter configuration or additional data analysis. Thus, the streamlined NGS library construction and comprehensive result output make Hi-TOM particularly suitable for high-throughput identification of all types of mutations induced by CRISPR/Cas systems.

## 与本项目（植物 CRISPR-Cas9 靶点效率预测）相关的关键结论

1. **突变检测端的高通量方案**：Hi-TOM 提供"固定桥接序列 + 条形码引物"的 NGS 文库构建策略，配合在线分析工具，可对**多个样本 × 多个靶位点**同时给出精确的突变类型和突变比例（percentage），把大规模突变筛查的成本和工作量大幅降低。
2. **适用于植物体系**：论文在水稻和六倍体小麦（以及人细胞）样本上验证了工具的高可靠性与高灵敏度——这意味着它可直接服务于植物基因编辑实验中"靶点效率的实验测定"环节，为预测模型提供标注数据（哪些 gRNA 真正高效）。
3. **对复杂嵌合突变敏感**：基因编辑常诱导复杂的嵌合/混合突变类型，Hi-TOM 能可靠追踪此类突变，比常规 TIDE/ICE 类工具更适合高通量场景。
4. **使用门槛低**：无需专门设计 barcode 引物、无需繁琐参数配置、无需额外数据分析；在线工具地址为 www.hi-tom.net/hi-tom/（注意：该站点近年曾出现访问不稳定，社区另有 Hi-TOM 2.0 / hi-tom.cn 镜像）。
5. **在项目流程中的定位**：Hi-TOM 属于"编辑结果检测"工具，与本项目的"编辑前靶点效率预测"（如 DeepSpCas9 类模型）形成互补——预测模型筛出的候选 gRNA 可借助 Hi-TOM 类高通量测序方案批量验证，从而获得训练/评估所需的真值数据。

## 来源

- PubMed: https://pubmed.ncbi.nlm.nih.gov/30446870/
- 出版社页面（付费墙）: https://link.springer.com/article/10.1007/s11427-018-9402-9
