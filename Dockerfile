FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

RUN mkdir -p /app/data /opt/factorio/saves /opt/factorio/backups /opt/factorio/config /opt/factorio/mods /opt/factorio/logs

ENV FACTORIO_DIR=/opt/factorio \
    DATA_DIR=/app/data \
    FRONTEND_DIST=/app/frontend/dist \
    TZ=Asia/Shanghai

EXPOSE 8199 34197/udp

VOLUME ["/app/data", "/opt/factorio"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8199"]
