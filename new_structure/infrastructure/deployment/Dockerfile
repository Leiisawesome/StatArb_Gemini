# Multi-stage Dockerfile for StatArb Gemini Production

# Stage 1: Build stage
FROM python:3.9-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY new_structure/infrastructure/deployment/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r trader && useradd -r -g trader trader

# Set work directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/trader/.local

# Copy application code
COPY new_structure/ ./
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p logs data config results && \
    chown -R trader:trader /app

# Switch to non-root user
USER trader

# Make sure scripts are executable
RUN chmod +x infrastructure/deployment/entrypoint.sh || true

# Add local bin to PATH
ENV PATH=/home/trader/.local/bin:$PATH

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["python", "main.py"]
