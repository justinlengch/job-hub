FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (separate from app code)
# This layer will only rebuild when dependencies change
COPY requirements.txt ./
COPY requirements.lock ./

# Install dependencies with cache mount (this layer gets cached until requirements change)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.lock

COPY apps/backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY apps/backend/app ./app

# Set defaults
EXPOSE 8000
ENV ENVIRONMENT=production

CMD ["/docker-entrypoint.sh"]
