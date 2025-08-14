FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV UV_HTTP_TIMEOUT=3600

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN useradd --create-home --shell /bin/bash appuser

COPY pyproject.toml uv.lock ./

RUN uv pip sync --system --no-cache pyproject.toml

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY app ./app

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Add a healthcheck to verify the app is running
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/docker-entrypoint.sh"]
