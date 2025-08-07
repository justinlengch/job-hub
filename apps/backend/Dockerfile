# Official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
# Set a longer timeout for uv to handle slower networks
ENV UV_HTTP_TIMEOUT=3600

# Set the working directory in the container
WORKDIR /app

# Install uv, the Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --system: Install packages into the system Python environment
# --no-cache: Disable caching to reduce image size
RUN uv pip sync --system --no-cache pyproject.toml

# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy the rest of the application code
COPY app ./app

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Add a healthcheck to verify the app is running
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the entrypoint script
CMD ["/docker-entrypoint.sh"]
