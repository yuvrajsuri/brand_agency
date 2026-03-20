FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for Playwright + Indic fonts
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    fontconfig \
    fonts-liberation \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8002/health')"

# Run the application
CMD ["python", "main.py"]
