# 计B 独立复核与敏感性实验（2026-09-19）

## A. QC 剔除一致性复核

- qc_excluded_0918.csv: 350 行 / 16 批次
- hitom_clean_merged_0918.csv 备注含 QC剔除: 347 行 / 全表 1361 行

剔除规则分布（按 qc 清单备注）:
0
无WT行          238
双峰40-60       103
非WT主型N%≥N%      9

逐批剔除数对账（清单 vs 报告声称）:
- USR-6883: 清单 82 / 报告 82（总 94）  ✅一致
- USR-6137: 清单 55 / 报告 55（总 80）  ✅一致
- USR-6444: 清单 33 / 报告 33（总 48）  ✅一致
- USR-7342: 清单 19 / 报告 19（总 26）  ✅一致

编号交集: qc清单 350 唯一ID,  merged QC行 347 唯一ID,  交集 347
- 仅在清单: ['TKS_1131', 'TKS_1134', 'TKS_1135']
- 交集行剔除原因文本不一致数: 0

## B. 已声明更正在现行基线表中的落地审计

基线表 hitom_seq30_full_0916.csv: 487 行

B1. LG01.6995/6999 行数: 35
    seq20 唯一值: ['CGTAAGGATTGCTGCTGAGA', 'TGTTCATCGGTGATCTCGAT']
    pam 唯一值: ['AGG']
    更正后期望 seq20=CGTAAGGATTGCTGCTGAGA, pam=AGG → seq ❌, pam ✅
    6995: 19 行, 坐标 165462948-165462968, 期望 165462914-165462934 ❌
    6999: 16 行, 坐标 165502832-165502852, 期望 165502832-165502852 ✅

B2. LG02.4820 行数: 6
seq20                 pam
TTCAAGTTCTAAGTAATCCT  CGG    6
    问题 guide AACATGGTTCGAGTTCAAGA 在基线表中: 0 行

B3. 基线表非 NGG PAM 行数: 0

B4. USR-5712 批行数: 61, indel_pct 中位数: 1.0000（problem2 称写回后中位数 1.0）
    重算表列: ['block', 'indel_left_published口径', 'indel_right_切割点侧']

## C. 100% 编辑行对基线 LOGO-CV 的敏感性

- indel_pct=1.0（round6）行数: 101 / 487
- 按基因分布:
gene_id
EVM.MODEL.LG01.555      4
EVM.MODEL.LG01.6995    16
EVM.MODEL.LG01.6999    13
EVM.MODEL.LG04.2802    19
EVM.MODEL.LG07.3296    41
EVM.MODEL.LG07.3933     8
- 按批次分布:
batch
USR-23709     2
USR-25902     2
USR-26162     4
USR-4411      4
USR-5712     41
USR-8145     48
- [baseline_all487] n=487, 基因分组=13, 有效折=6, LOGO-CV 中位 rho = 0.4038
- [drop_indel_eq_1] n=386, 基因分组=13, 有效折=5, LOGO-CV 中位 rho = 0.5963
- [drop_USR8145] n=375, 基因分组=10, 有效折=6, LOGO-CV 中位 rho = 0.4768

Saved results/b_sensitivity_logo_0919.csv