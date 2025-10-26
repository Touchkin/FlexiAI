# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy FlexiAI package files
COPY flexiai/ /app/flexiai/
COPY setup.py /app/
COPY README.md /app/
COPY pyproject.toml /app/

# Install FlexiAI package
RUN pip install --no-cache-dir -e .

# Copy example application
COPY examples/fastapi_multiworker/app.py /app/app.py
COPY examples/fastapi_multiworker/requirements.txt /app/requirements.txt

# Install application dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
