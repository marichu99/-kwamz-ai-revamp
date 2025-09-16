# Use Python slim-bullseye for better Playwright support
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    git \
    curl \
    wget \
    gnupg \
    netcat \
    unzip \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    postgresql-client \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (as root for system-wide access)
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright system dependencies as root
RUN pip install playwright && playwright install-deps

# Copy application code
COPY . .

# Copy entrypoint script and set permissions
COPY entryPoint.sh /app/entryPoint.sh
RUN chmod +x /app/entryPoint.sh

# Create a non-root user for security and set permissions
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app

# Switch to non-root user BEFORE installing browsers
USER flaskuser

# Install Playwright browsers as the flaskuser (this is the key fix!)
RUN playwright install chromium

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/home/flaskuser/.cache/ms-playwright

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Set entrypoint and default command
ENTRYPOINT ["/app/entryPoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]