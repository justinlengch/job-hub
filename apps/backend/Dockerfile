FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=3600
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN useradd --create-home --shell /bin/bash appuser

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-cache

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -c "import uvicorn, click; print('Deps OK:', uvicorn.__version__, click.__version__)"

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY app ./app
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/docker-entrypoint.sh"]
