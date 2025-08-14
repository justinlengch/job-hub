#!/bin/sh

# Use PORT environment variable if set (for Heroku, Railway, etc.), otherwise default to 8000
PORT=${PORT:-8000}

if [ "$ENVIRONMENT" = "development" ]; then
    echo "Starting in development mode with auto-reload on port $PORT..."
    exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $PORT --log-level debug
else
    echo "Starting in production mode on port $PORT..."
    exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level info
fi
