# ============================
# STAGE 1: Frontend builder (React/Vite)
# ============================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ============================
# STAGE 2: Python dependency builder
# Installs the venv and compiles any native extensions (e.g. miniaudio on
# arm64), then the final stage copies only the finished venv. Compilers,
# build tools and the uv cache never reach the runtime image.
# ============================
FROM python:3.11-slim AS deps-builder

ENV UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy

# build-essential provides gcc/g++ for compiling miniaudio (needed on arm64;
# on x86_64 a manylinux wheel is used instead).
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project && \
    rm -rf /root/.cache/uv

# ============================
# STAGE 3: Runtime (slim)
# ============================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    AI_PROVIDER=mock

# Runtime shared library for faster-whisper (ctranslate2). No compiler needed.
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Copy the pre-built venv (same absolute path so relocatable shebangs work).
COPY --from=deps-builder /app/backend/.venv /app/backend/.venv

# Copy the backend source and the built frontend SPA.
COPY backend/ ./
# Strip any .env files that may have slipped through dockerignore —
# secrets must never be baked into the image.
RUN find . -name '.env*' -type f -delete 2>/dev/null || true
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Keep the image lean: no tests, no compiled bytecode, no __pycache__.
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
    find . -name "*.pyc" -delete 2>/dev/null || true

ENV PATH="/app/backend/.venv/bin:$PATH"

# Pre-cache the faster-whisper model so the first STT call is instant
# (no runtime download, no HF_TOKEN warning, no cold-start latency).
ENV HF_HOME=/app/backend/.cache/huggingface
RUN HF_HUB_OFFLINE=0 python3 <<'PYEOF' && echo "whisper-pre-cache OK" || echo "whisper-pre-cache skipped (no network at build time)"
from faster_whisper import WhisperModel
_ = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Whisper model cached")
PYEOF
# At runtime the model is already in the image cache — no Hub calls needed.
ENV HF_HUB_OFFLINE=1

EXPOSE 8080

# Render injects $PORT at runtime; fall back to 8080 for local builds.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]