#!/bin/bash
# Production deployment script for Job Hub backend

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENVIRONMENT="production"

# Run with production settings
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000
