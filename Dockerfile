# ACIT Gateway - uv-based multi-stage build
# Python 3.11 slim for smaller image

# ---- Build stage ----
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set uv to link mode for faster installs and smaller images
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ ./src/

# Install the project
RUN uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.11-slim AS runtime

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy source code
COPY --from=builder --chown=app:app /app/src /app/src

# Seed Catalog. tests/ is not in the image and /app/data is bind-mounted, so
# this is the only candidate _default_catalog_file() can resolve at runtime.
COPY --chown=app:app catalogs.json /app/catalogs.json

# Create data directory
RUN mkdir -p /app/data && chown -R app:app /app/data

# Use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]