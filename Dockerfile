# syntax=docker/dockerfile:1.7
FROM node:22.14.0-alpine3.21 AS frontend-build

WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM python:3.13.2-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    SERVE_FRONTEND=true \
    FRONTEND_DIR=/app/frontend/dist \
    ANAC_DATA_FILE=/app/data_voo/dados_completos.parquet \
    ALLOWED_ORIGINS= \
    MAX_PERIOD_MONTHS=120 \
    RATE_LIMIT_PER_MINUTE=120

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY backend/requirements-prod.txt /tmp/requirements.txt
RUN pip install --requirement /tmp/requirements.txt
COPY --chown=app:app backend/ ./backend/
COPY --from=frontend-build --chown=app:app /build/frontend/dist ./frontend/dist

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"]

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]
