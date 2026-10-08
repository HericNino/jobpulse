# syntax=docker/dockerfile:1
#
# Stage 1 installs dependencies and builds the DuckDB warehouse from data/postings.jsonl.
# Stage 2 keeps only the virtualenv and the warehouse file and runs the API as a non-root user.

FROM python:3.12-slim AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app

# dependencies first, so code changes don't invalidate these layers
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project --extra pipeline
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --extra pipeline

COPY transform ./transform
COPY data/postings.jsonl ./data/postings.jsonl
ENV JOBPULSE_TRANSFORM_DIR=/app/transform
RUN .venv/bin/jobpulse warehouse --data data --out /app/warehouse.duckdb

# a second, much smaller environment with only what the API imports (no dbt, no Anthropic SDK)
# installed at the same path it runs from: venv scripts hard-code their location
RUN UV_PROJECT_ENVIRONMENT=/app/runtime uv sync --locked --no-dev --no-editable --extra api


FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/HericNino/jobpulse" \
      org.opencontainers.image.description="Read-only API over daily tech job posting statistics" \
      org.opencontainers.image.licenses="MIT"
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /app/runtime /app/runtime
COPY --from=build /app/warehouse.duckdb /app/warehouse.duckdb
ENV PATH=/app/runtime/bin:$PATH \
    JOBPULSE_WAREHOUSE=/app/warehouse.duckdb \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["uvicorn", "jobpulse.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
