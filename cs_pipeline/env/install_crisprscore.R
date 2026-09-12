# crisprScore 安装与示例验证（A0 节）
# 用法（Anaconda Prompt）：
#   conda activate crispr
#   Rscript env/install_crisprscore.R
#
# 说明：bioconductor.org 在本网络不可达，BiocManager 无法校验版本，
# 故绕过 BiocManager，直接把 repo 指向westlake 镜像的 Bioc 3.18（对应 R 4.3）。
options(repos = c(
  CRAN    = "https://mirrors.tuna.tsinghua.edu.cn/CRAN",
  BioCsoft = "https://mirrors.westlake.edu.cn/bioconductor/packages/3.18/bioc",
  BioCann  = "https://mirrors.westlake.edu.cn/bioconductor/packages/3.18/data/annotation",
  BioCexp  = "https://mirrors.westlake.edu.cn/bioconductor/packages/3.18/data/experiment"
))
install.packages("crisprScore")  # 已装则秒过

# basilisk 自带的 Miniconda 4.12.0 太旧，连清华镜像都 TLS 失败；改用系统 conda（26.x）
Sys.setenv(BASILISK_EXTERNAL_CONDA = "D:/Miniconda")
library(crisprScore)
source("env/patch_basilisk.R")   # Windows 下绕过 basilisk 激活 bug，必须先打补丁再打分
patch_basilisk()
Sys.setenv(PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple")  # basilisk 建环境时装 TF2 走清华镜像
# 示例验证：30bp = 4nt上游 + 20nt guide + 3nt PAM + 3nt下游；返回一个数值即成功
# 首次调用 basilisk 会创建隔离 conda 环境并 pip 安装依赖（10-20 分钟，需联网），属正常
print(getDeepSpCas9Scores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC"))
print(getCRISPRonScores("ATCGGCTAAGCTAGGCTAGCATCGTGGATC"))
cat("crisprScore OK\n")
