FROM python:3.13-slim

WORKDIR /app

# Install NATS client
RUN pip install --no-cache-dir nats-py==2.10.0

# Copy init scripts
COPY init_streams.py /app/init_streams.py
COPY delete_streams.py /app/delete_streams.py

# Create non-root user
RUN groupadd -r jobuser && \
    useradd -r -g jobuser -u 1000 jobuser && \
    chown -R jobuser:jobuser /app

# Switch to non-root user
USER jobuser

# Default: init streams
CMD ["python", "/app/init_streams.py"]

