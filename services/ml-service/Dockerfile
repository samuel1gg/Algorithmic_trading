FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY shared/ /app/shared/
COPY database/ /app/database/
COPY services/ml-service/ /app/

# Create models directory
RUN mkdir -p /app/models

# Set Python path
ENV PYTHONPATH=/app

# Run the service
CMD ["python", "main.py"]

