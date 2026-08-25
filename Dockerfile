FROM node:22-alpine AS webbuilder

WORKDIR /web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
# vite outDir is ../src/web/static -> /src/web/static in this stage
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder


WORKDIR /app

# Copy manifests
COPY pyproject.toml uv.lock ./

# Create .venv
RUN uv sync --frozen --no-dev --compile-bytecode --no-cache

# Runner
FROM python:3.12-slim-trixie AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app


# Copy .venv and application code
COPY --from=builder /app/.venv .venv
COPY src/ src/
COPY --from=webbuilder /src/web/static/ src/web/static/
COPY run.py ./

# Compile application code to bytecode
RUN python -m compileall src/ run.py

# Config web UI
EXPOSE 8080

# Default command runs your launcher, which invokes .venv/bin/python
CMD ["python", "run.py"]