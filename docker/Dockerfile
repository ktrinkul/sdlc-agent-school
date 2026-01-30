FROM python:3.11-slim

# Install git (required for gitpython)
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY prompts/ ./prompts/

# Set Python path
ENV PYTHONPATH=/app

# Entrypoint
ENTRYPOINT ["python", "-m", "src.cli"]
