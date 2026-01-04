# Dockerfile for Collision Detection System
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY raspberry-pi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY raspberry-pi/ .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs

# Set environment variables
ENV UPLOAD_FOLDER=/app/uploads
ENV LOG_DIRECTORY=/app/logs
ENV HOST=0.0.0.0
ENV PORT=5000

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "-m", "collision_server.main"]