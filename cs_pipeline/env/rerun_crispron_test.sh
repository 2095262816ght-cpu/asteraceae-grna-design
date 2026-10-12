#!/usr/bin/env bash
# 统一换行符后重跑 CRISPRon 官方测试
set -euo pipefail
D=$(cd "$(dirname "$0")/../tools/CRISPRon" && pwd)
cd "$D"
find . -path ./.git -prune -o -type f \( -name '*.sh' -o -name '*.py' -o -name '*.fa' -o -name '*.csv' -o -name '*.tsv' -o -name '*.md' \) -print0 | xargs -0 sed -i 's/\r$//'
source ~/miniconda3/etc/profile.d/conda.sh
conda activate crispron
rm -rf test/outdir.test
bash bin/test.sh
