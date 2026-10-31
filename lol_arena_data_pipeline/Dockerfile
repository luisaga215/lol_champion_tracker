FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src

ENV DATABASE_PATH=/app/data/arena_pipeline.db \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    SCHEDULER_ENABLED=true \
    CRAWLER_INTERVAL_SECONDS=900 \
    CRAWLER_SEED_PUUIDS=[]

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
