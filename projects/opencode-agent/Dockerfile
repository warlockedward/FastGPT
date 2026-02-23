# AI Workflow Generator - Python Agent Dockerfile
#
# Build:
#   docker build -t fastgpt-ai-workflow-agent:latest -f Dockerfile .
#
# Run:
#   docker run -p 8000:8000 --env-file .env fastgpt-ai-workflow-agent:latest

# ========================
# Base Image
# ========================
FROM python:3.11-slim

# ========================
# Set Environment
# ========================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ========================
# Set Working Directory
# ========================
WORKDIR /app

# ========================
# Install System Dependencies
# ========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ========================
# Copy Project Files
# ========================
COPY pyproject.toml .

# ========================
# Install Python Dependencies
# ========================
RUN pip install --no-cache-dir \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    pydantic>=2.0.0 \
    httpx>=0.25.0 \
    python-dotenv>=1.0.0

# ========================
# Copy Source Code
# ========================
COPY src/ ./src/

# ========================
# Expose Port (configurable)
# ========================
# Default port can be overridden via PORT env var
EXPOSE 8000

# ========================
# Health Check
# ========================
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ========================
# Run Application
# ========================
# Use PORT env var if set, default to 8000
CMD ["sh", "-c", "uvicorn src.api.routes:app --host 0.0.0.0 --port ${PORT:-8000}"]
