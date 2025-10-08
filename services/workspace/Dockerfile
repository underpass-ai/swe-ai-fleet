# Multi-stage build for Workspace Scoring Service
FROM docker.io/library/golang:1.23-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git make protobuf-dev

WORKDIR /build

# Copy go mod files
COPY services/go.mod services/go.sum* ./
RUN go mod download || true

# Copy source
COPY services/ .

# Build the service
WORKDIR /build/workspace/cmd
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags '-w -s' -o /workspace .

# Production image
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copy binary
COPY --from=builder /workspace /app/workspace

# Copy config files
COPY config/ /app/config/

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 50053

ENV RIGOR_CONFIG=/app/config/rigor.yaml
ENV PORT=50053

ENTRYPOINT ["/app/workspace"]

