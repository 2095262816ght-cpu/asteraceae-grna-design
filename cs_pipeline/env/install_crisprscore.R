# crisprScore 安装与示例验证（A0 节）
# 用法（Anaconda Prompt）：
#   conda activate crispr
#   Rscript env/install_crisprscore.R
if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
BiocManager::install("crisprScore")  # 依赖较多，首次约 20-40 分钟

library(crisprScore)
# 示例验证：30bp = 4nt上游 + 20nt guide + 3nt PAM + 3nt下游；返回一个数值即成功
# 首次调用 basilisk 会自动下载隔离 conda 环境（10-20 分钟，需联网），属正常
print(getDeepSpCas9Scores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC"))
print(getCRISPRonScores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC"))
cat("crisprScore OK\n")
