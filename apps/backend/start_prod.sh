#!/bin/bash

# Production server startup script
echo "Starting Job Hub Backend (Production Mode)..."

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "Error: Please run this script from the apps/backend directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set production environment variables
export ENVIRONMENT=production
export LOG_LEVEL=info

# Start the server with multiple workers
echo "Starting uvicorn server with 4 workers..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info

echo "Server stopped."
