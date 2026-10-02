FROM python:3.10-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 1. 系统依赖：bash/sed（CRISPRon 脚本执行与 CRLF 治理）、bzip2（micromamba 解压）、curl/ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash sed bzip2 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. 打分环境 venv-score：DeepSpCas9/genet（TF<2.10 口径，对齐 Windows conda crispr 环境实测版本）
COPY cs_pipeline/requirements-score.txt /tmp/requirements-score.txt
RUN python -m venv /opt/venv-score \
    && /opt/venv-score/bin/pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/requirements-score.txt

# 3. CRISPRon 环境 venv-crispron：TF2.14 口径（对齐 WSL conda crispron 环境实测版本）
COPY cs_pipeline/requirements-crispron.txt /tmp/requirements-crispron.txt
RUN python -m venv /opt/venv-crispron \
    && /opt/venv-crispron/bin/pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /tmp/requirements-crispron.txt

# 4. ViennaRNA 2.6.4：bioconda（与 WSL 训练同一 conda 包）；apt bookworm 仅 2.5.1 且在 non-free，弃用
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C /usr/local bin/micromamba \
    && /usr/local/bin/micromamba create -y -r /opt/mamba -p /opt/viennarna \
         -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge \
         -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda \
         viennarna=2.6.4 \
    && rm -rf /root/.cache /opt/mamba /opt/viennarna/pkgs
ENV PATH=/opt/viennarna/bin:$PATH
RUN RNAfold --version 2>&1 | grep -q "2.6.4"

# 5. web 栈装进系统 python（显式 /usr/local/bin/pip：viennarna 环境自带 python3.12 且在 PATH 前排，裸 pip 会装错解释器）
COPY backend/requirements.txt /app/backend/requirements.txt
RUN /usr/local/bin/pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r /app/backend/requirements.txt

# 6. 业务代码
COPY cs_pipeline /app/cs_pipeline
COPY backend /app/backend

# 7. CRLF 治理 + 可执行位（构建上下文来自 Windows 工作树，对照 env/setup_crispron_wsl.sh 同款处理）
RUN sed -i 's/\r$//' /app/cs_pipeline/tools/CRISPRon/bin/*.sh /app/cs_pipeline/tools/CRISPRon/bin/*.py \
    && chmod +x /app/cs_pipeline/tools/CRISPRon/bin/*.sh /app/cs_pipeline/tools/CRISPRon/bin/*.py

# 8. genet 权重固化（复刻 deploy_demo_cn.ps1 兜底约定：本地 checkpoint 拷入 genet 包内 models 目录，避免运行时 GitHub 下载）
RUN GMD=$(/opt/venv-score/bin/python -c "import inspect,os,genet.models;print(os.path.dirname(inspect.getfile(genet.models)))") \
    && mkdir -p "$GMD/DeepSpCas9" \
    && cp /app/cs_pipeline/models/DeepSpCas9/PreTrain-Final-* "$GMD/DeepSpCas9/"

# 9. 环境接线（CRISPR_PYTHON 命中 InferenceClient._resolve_crispr_python 第一优先级；CRISPRON_MODE=native 走容器内原生管线）
ENV CRISPR_PYTHON=/opt/venv-score/bin/python \
    CRISPRON_PYTHON=/opt/venv-crispron/bin/python3 \
    CRISPRON_MODE=native

# 10. 构建期 smoke：锚点序列真值全链路断言（已知真值 DeepSpCas9=71.2494 / CRISPRon=59.61），断则 build 失败
#     锁死：TF2.9×genet×本地权重、TF2.14×keras SavedModel、RNAfold 2.6.4、GLMM joblib、native 分支 PATH 解析
RUN /opt/venv-score/bin/python -c "import subprocess,sys;p=subprocess.run([sys.executable,'/app/cs_pipeline/app/score_deepspcas9_cli.py'],input='ATCGGCTAAGCTAGGCTAGCATCGTGGATC\n',capture_output=True,text=True);assert p.returncode==0,p.stderr[-2000:];line=p.stdout.strip().splitlines()[-1];f=line.split(',');assert abs(float(f[1])-71.2494)<=0.05,line;assert abs(float(f[2])-59.61)<=0.05,line;assert f[3]=='wsl_real',line;print('CLI smoke OK:',line)"
RUN /opt/venv-score/bin/python -c "import sys;sys.path.insert(0,'/app/cs_pipeline');from scripts.predict import predict_details;r=predict_details(['ATCGGCTAAGCTAGGCTAGCATCGTGGATC']).iloc[0];assert r['crispron_source']=='wsl_real',dict(r);assert abs(float(r['crispron_score'])-59.61)<=0.5,dict(r);print('CRISPRon smoke OK:',dict(r))"

EXPOSE 8000

# 启动容器时执行全自动建表灌库，随后拉起 Uvicorn 服务（显式系统 python：PATH 前排的 viennarna 自带 python3.12）
CMD ["sh", "-c", "/usr/local/bin/python -m backend.app.db.seed && /usr/local/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
