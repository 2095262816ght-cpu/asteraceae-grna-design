#!/usr/bin/env bash
# 在 WSL Ubuntu 中搭建 CRISPRon 环境（降级方案1的 CRISPRon 部分）
# 用法（Windows 侧）：
#   wsl -d Ubuntu-22.04 -- bash /mnt/d/lifesciencechallenge/cs_pipeline/env/setup_crispron_wsl.sh
set -euo pipefail

source ~/miniconda3/etc/profile.d/conda.sh
D=/mnt/d/lifesciencechallenge/cs_pipeline/tools/CRISPRon

echo "[1/5] create crispron env"
if conda env list | grep -q "^crispron "; then
  echo "crispron env exists, skip"
else
  conda create -n crispron -y -c conda-forge -c bioconda \
    python=3.10 tensorflow=2.14 viennarna=2.6.4 biopython pandas numpy scikit-learn
fi

echo "[2/5] download CRISPRoff components"
mkdir -p ~/crisproff_dl && cd ~/crisproff_dl
[ -f crisproff-1.1.2.tar.gz ] || wget -q https://rth.dk/resources/crispr/crisproff/downloads/crisproff-1.1.2.tar.gz
[ -f CRISPRspec_CRISPRoff_pipeline.v1.1.1.tar.gz ] || wget -q https://rth.dk/resources/crispr/crisproff/downloads/CRISPRspec_CRISPRoff_pipeline.v1.1.1.tar.gz
tar xzf crisproff-1.1.2.tar.gz
tar xzf CRISPRspec_CRISPRoff_pipeline.v1.1.1.tar.gz

echo "[3/5] locate files"
PIPELINE=$(find ~/crisproff_dl -name "CRISPRspec_CRISPRoff_pipeline.py" | head -1)
ENERGY=$(find ~/crisproff_dl -name "energy_dics.pkl" | head -1)
echo "pipeline: $PIPELINE"
echo "energy:   $ENERGY"
[ -n "$PIPELINE" ] && [ -n "$ENERGY" ]

echo "[4/5] assemble into CRISPRon"
mkdir -p "$D/data/model"
cp "$PIPELINE" "$D/bin/"
cp "$ENERGY" "$D/data/model/energy_dics.pkl"
chmod +x "$D"/bin/*.py "$D"/bin/*.sh
sed -i 's/\r$//' "$D"/bin/*.sh "$D"/bin/*.py   # Windows git 可能检出 CRLF

echo "[5/5] run built-in test"
cd "$D"
conda activate crispron
bash bin/test.sh
echo CRISPRON_SETUP_DONE
