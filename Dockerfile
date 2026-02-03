# STOM CLI Docker Image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements-cli.txt .
RUN pip install --no-cache-dir -r requirements-cli.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p _database _log logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STOM_CLI_MODE=1

# Entry point
ENTRYPOINT ["python", "-m", "cli.main"]
CMD ["--help"]
