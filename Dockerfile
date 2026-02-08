FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies (including fonts for Indic support)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    fonts-noto-core \
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
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["python", "main.py"]
