#!/usr/bin/env bash
# Windows 原生（Git Bash + conda env crispron-win）运行 CRISPRon 管线
# 由 scripts/03_score_crispron.py 在 WSL 不可用时自动降级调用。
# 依据：env/crispron_win_native_0909.md（9.9 已验证，内置测试逐字节一致）。
# 输入:  data/hitom/crispron_io/seq30_in.fa
# 输出:  data/hitom/crispron_io/out/crispron.csv
set -euo pipefail
D="$(cd "$(dirname "$0")/.." && pwd)"          # cs_pipeline/
CRISPRON_WIN_ENV="$HOME/anaconda3/envs/crispron-win"
export PATH="$D/tools/win-shims:$D/tools/ViennaRNA/bin:$CRISPRON_WIN_ENV:$CRISPRON_WIN_ENV/Scripts:$PATH"
cd "$D/tools/CRISPRon"
bash bin/CRISPRon.sh "$D/data/hitom/crispron_io/seq30_in.fa" "$D/data/hitom/crispron_io/out"
