FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir nats-py==2.9.0

# Copy test script
COPY jobs/test-auto-dispatch/test_auto_dispatch.py /app/test_auto_dispatch.py

# Run as non-root
USER 1000:1000

CMD ["python", "test_auto_dispatch.py"]

