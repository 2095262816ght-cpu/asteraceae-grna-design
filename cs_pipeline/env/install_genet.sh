#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
source /d/Miniconda/etc/profile.d/conda.sh
conda activate crispr
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple genet > env/pip_genet.log 2>&1
echo "PIP_EXIT=$?" >> env/pip_genet.log
python -c "
from genet.predict import DeepSpCas9
m = DeepSpCas9()
print(m.predict('ATCGGCTAAGCTAGGCTAGCATCGTGGATC'))
print('GENET_DEEPSPCAS9_OK')" >> env/pip_genet.log 2>&1
echo "TEST_EXIT=$?" >> env/pip_genet.log
