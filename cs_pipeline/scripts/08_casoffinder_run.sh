#!/usr/bin/env bash
# 08: Cas-OFFinder 脱靶预测，见《分工详案_计算机系》（docs/plans/division_plan_cs.md）B3 节
# 输入文件 data/lettuce/casoffinder_input.txt 格式：
#   第1行 染色体 fasta 目录（多条记录需先拆成每条染色体一个 .fa 放 data/lettuce/chrs/）
#   第2行 20 个 N + PAM 模式（NNNNNNNNNNNNNNNNNNNNNNGG）
#   之后每行 一条候选 guide 序列 + 允许错配数（取 3）
# 第三个参数 C = CPU；有 NVIDIA 显卡可用 G
set -euo pipefail
tools/cas-offinder.exe data/lettuce/casoffinder_input.txt C results/offtarget_raw_0924.txt
