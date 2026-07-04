FROM node:22-alpine AS frontend

WORKDIR /frontend
RUN corepack enable && corepack prepare pnpm@11.7.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    CONTENT_FACTORY_ROOT=/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl espeak-ng ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY content_factory ./content_factory
RUN pip install --no-cache-dir .

COPY config ./config
COPY examples ./examples
COPY main.py ./main.py
COPY --from=frontend /frontend/dist ./frontend_dist

RUN mkdir -p /data

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl --fail http://127.0.0.1:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
