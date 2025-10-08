# Multi-stage build for Story Coach Service
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
WORKDIR /build/storycoach/cmd
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags '-w -s' -o /storycoach .

# Production image
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copy binary
COPY --from=builder /storycoach /app/storycoach

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 50052

ENV PORT=50052

ENTRYPOINT ["/app/storycoach"]

