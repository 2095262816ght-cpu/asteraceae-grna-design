# -*- coding: utf-8 -*-
"""灌库后验证：gene_expressions 表达证据完整性（全基因组 crosswalk 接线后）。

检查项：
1. 双命名空间基因均有表达记录；
2. is_mappable=True 的记录必有 TPM/tau/top_tissue，且 lsa_id 非空；
3. is_mappable=False 的记录必无 TPM（不编造）且有缺失原因；
4. LsT2T* 命名空间的可映射占比（期望与 crosswalk tier1-3 + 表达矩阵收录一致）。
"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

conn = sqlite3.connect("lifescience.db")
c = conn.cursor()

def q(sql):
    c.execute(sql)
    return c.fetchall()

total = q("SELECT COUNT(*) FROM gene_expressions")[0][0]
wide = q("SELECT COUNT(*) FROM gene_expressions WHERE gene_id LIKE 'LsT2T%'")[0][0]
nlr = q("SELECT COUNT(*) FROM gene_expressions WHERE gene_id LIKE 'LsaT2T%'")[0][0]
mappable = q("SELECT COUNT(*) FROM gene_expressions WHERE is_mappable = 1")[0][0]
wide_map = q("SELECT COUNT(*) FROM gene_expressions WHERE gene_id LIKE 'LsT2T%' AND is_mappable = 1")[0][0]
nlr_map = q("SELECT COUNT(*) FROM gene_expressions WHERE gene_id LIKE 'LsaT2T%' AND is_mappable = 1")[0][0]

bad_mapped = q("""
    SELECT COUNT(*) FROM gene_expressions WHERE is_mappable = 1
    AND (tpm_root IS NULL OR tau IS NULL OR top_tissue IS NULL OR lsa_id IS NULL)
""")[0][0]
bad_unmapped = q("""
    SELECT COUNT(*) FROM gene_expressions WHERE is_mappable = 0
    AND (tpm_root IS NOT NULL OR tpm_leaf IS NOT NULL OR unmappable_reason IS NULL)
""")[0][0]

print(f"表达记录总数: {total}（LsT2T* {wide}，LsaT2T* {nlr}）")
print(f"可映射: {mappable}（LsT2T* {wide_map}/{wide}，LsaT2T* {nlr_map}/{nlr}）")
print(f"[1] is_mappable=1 但缺 TPM/tau/top_tissue/lsa_id: {bad_mapped}（应为 0）")
print(f"[2] is_mappable=0 但带 TPM 或缺缺失原因: {bad_unmapped}（应为 0）")

print("\n抽样（LsT2T* 可映射 3 条）:")
for r in q("""
    SELECT gene_id, lsa_id, tier, top_tissue, top_tpm, tau FROM gene_expressions
    WHERE gene_id LIKE 'LsT2T%' AND is_mappable = 1 LIMIT 3
"""):
    print("  ", r)
print("抽样（LsT2T* 缺失 3 条）:")
for r in q("""
    SELECT gene_id, tier, substr(unmappable_reason, 1, 40) FROM gene_expressions
    WHERE gene_id LIKE 'LsT2T%' AND is_mappable = 0 LIMIT 3
"""):
    print("  ", r)

ok = bad_mapped == 0 and bad_unmapped == 0 and wide_map > 0 and nlr_map == 35
print("\n结论:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
