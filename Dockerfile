# Use official Python slim image
FROM python:3.12-slim

# Install system dependencies for rasterio/GDAL
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env variable
ENV PORT=8000
EXPOSE $PORT

# Start the application
CMD uvicorn src.main:app --host 0.0.0.0 --port $PORT
