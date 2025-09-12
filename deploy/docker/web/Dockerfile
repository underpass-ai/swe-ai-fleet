# syntax=docker/dockerfile:1

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy project files needed for install
COPY pyproject.toml README.md /app/
COPY src /app/src

# Install package with web extras
RUN pip install --upgrade pip && pip install -e .[web]

EXPOSE 8080

ENV HOST=0.0.0.0 \
    PORT=8080 \
    REDIS_URL=redis://:swefleet-dev@host.docker.internal:6379/0 \
    NEO4J_URI=bolt://host.docker.internal:7687 \
    NEO4J_USER=neo4j \
    NEO4J_PASSWORD=test

CMD ["swe_ai_fleet-web"]


