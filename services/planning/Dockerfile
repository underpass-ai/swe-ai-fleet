# Multi-stage build for Planning Service
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
WORKDIR /build/planning/cmd
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags '-w -s' -o /planning .

# Production image
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copy binary
COPY --from=builder /planning /app/planning

# Copy config files
COPY config/ /app/config/

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 50051

ENV FSM_CONFIG=/app/config/agile.fsm.yaml
ENV NATS_URL=nats://nats:4222
ENV PORT=50051

ENTRYPOINT ["/app/planning"]

