# Multi-stage build for efficient image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.7.0
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.poetry

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add Poetry to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Install the package
RUN poetry build && pip install dist/*.whl

# Final stage - runtime image
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r ledzephyr && useradd -r -g ledzephyr ledzephyr

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/lz /usr/local/bin/lz
COPY --from=builder /usr/local/bin/ledzephyr /usr/local/bin/ledzephyr

# Create app directory
WORKDIR /app

# Create cache directory with proper permissions
RUN mkdir -p /app/.ledzephyr_cache && \
    chown -R ledzephyr:ledzephyr /app

# Switch to non-root user
USER ledzephyr

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LEDZEPHYR_CACHE_DIR=/app/.ledzephyr_cache

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD lz --version || exit 1

# Default command
ENTRYPOINT ["lz"]
CMD ["--help"]