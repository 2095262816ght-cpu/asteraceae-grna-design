FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY cs_pipeline /app/cs_pipeline
COPY backend /app/backend

EXPOSE 8000

# 启动容器时执行全自动建表灌库，随后拉起 Uvicorn 服务
CMD ["sh", "-c", "python -m backend.app.db.seed && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
