"""测试环境：禁用真实 T2T 基因组，避免导出测试触发全基因组脱靶扫描。

需要真实扫描语义的单测自行传入合成基因组路径（offtarget_service 显式参数）。
"""
import os

os.environ.setdefault("T2T_GENOME_FASTA", "tests/_genome_disabled_for_tests.fa")
# 测试与演示库隔离：测试夹具会清空 scoring_jobs/genes/target_candidates 等表，
# 绝不能让 pytest 触碰正式 lifescience.db（测试走独立的 lifescience_test.db）
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./lifescience_test.db")
