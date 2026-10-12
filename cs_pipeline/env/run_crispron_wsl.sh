#!/usr/bin/env bash
# 在 WSL 的 crispron 环境中运行 CRISPRon 管线（由 scripts/03_score_crispron.py 调用）
# 输入:  data/hitom/crispron_io/seq30_in.fa
# 输出:  data/hitom/crispron_io/out/crispron.csv
set -euo pipefail
source ~/miniconda3/etc/profile.d/conda.sh
conda activate crispron
D=$(cd "$(dirname "$0")/.." && pwd)
cd "$D/tools/CRISPRon"
bash bin/CRISPRon.sh "$D/data/hitom/crispron_io/seq30_in.fa" "$D/data/hitom/crispron_io/out"
