# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi:application \
    FLASK_ENV=production \
    NLTK_DATA=/app/nltk_data

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/app/static/documents \
    /app/app/static/index \
    /app/nltk_data

# Copy requirements first
COPY requirements.txt .

# Clean pip cache and install dependencies
RUN pip cache purge && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data with correct permissions
RUN python -c "import nltk; nltk.download('punkt', download_dir='/app/nltk_data'); nltk.download('punkt_tab', download_dir='/app/nltk_data'); nltk.download('stopwords', download_dir='/app/nltk_data'); nltk.download('wordnet', download_dir='/app/nltk_data')"

# Copy the application
COPY . .

# Set permissions for all directories
RUN chown -R nobody:nogroup /app && \
    chmod -R 755 /app

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 5000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--log-level", "debug", "--reload", "wsgi:application"]