FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install system dependencies including audio libraries for FastRTC
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    libportaudio2 \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
# Install FastRTC with all required features
RUN pip install --no-cache-dir fastrtc[vad,stt,tts]==0.0.23 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application (using the REST version)
CMD ["uvicorn", "src.main_rest:app", "--host", "0.0.0.0", "--port", "8080"] 