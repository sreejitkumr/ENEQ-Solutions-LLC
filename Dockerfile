# Multi-stage Docker build for ENEQ Quotation Generator

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create data directory for persistence
RUN mkdir -p /app/data /app/assets

# Expose port
EXPOSE 8501

# Set streamlit configuration
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_CLIENT_TOOLBAR_POSITION=bottom

# Health check
HEALTHCHECK CMD python -c "import requests; requests.get('http://localhost:8501', timeout=5)"

# Run the application
CMD ["streamlit", "run", "app.py"]
