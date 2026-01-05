# =============================================================================
# Scripts Dockerfile (데이터 Import, 유틸리티 스크립트용)
# =============================================================================
# NOTE: scripts와 apps(모델 포함)는 이미지에 포함됨. data 폴더는 S3에서 다운로드
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# 기본 빌드 도구 및 Playwright 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    # Playwright browser dependencies
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Common Requirements
COPY infra/docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for crawling)
RUN playwright install --with-deps chromium

# Install ML Dependencies for Reco Models (CPU-only to save space)
RUN pip install --no-cache-dir \
    "torch>=2.1" --extra-index-url https://download.pytorch.org/whl/cpu \
    "xgboost>=2.0.0" \
    "lightgbm>=4.0"

# Copy Code & Models (Bake into image)
COPY libs /libs
COPY scripts /app/scripts
COPY apps /app/apps

# PYTHONPATH includes /data for runtime data access
ENV PYTHONPATH=/app:/libs:/data

CMD ["python", "-u"]
