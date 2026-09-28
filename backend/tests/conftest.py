"""测试环境：禁用真实 T2T 基因组，避免导出测试触发全基因组脱靶扫描。

需要真实扫描语义的单测自行传入合成基因组路径（offtarget_service 显式参数）。
"""
import os

os.environ.setdefault("T2T_GENOME_FASTA", "tests/_genome_disabled_for_tests.fa")
