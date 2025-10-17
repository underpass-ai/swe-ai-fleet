FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .
COPY sources/ ./sources/

# Create non-root user
RUN useradd -m -u 1000 monitoring && chown -R monitoring:monitoring /app
USER monitoring

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')"

# Run server
CMD ["python", "server.py"]

