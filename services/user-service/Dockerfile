# syntax=docker/dockerfile:1.7

# ---- Proto generation stage ----
FROM docker.io/library/golang:1.25-alpine AS proto-builder
RUN apk add --no-cache protobuf
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /proto
COPY specs/fleet/user/v1/user.proto /proto/

RUN mkdir -p /gen/userv1 && \
    protoc -I/proto \
    --go_out=/gen/userv1 --go_opt=paths=source_relative \
    --go-grpc_out=/gen/userv1 --go-grpc_opt=paths=source_relative \
    user.proto

# ---- Build stage (Debian — go-duckdb requires glibc) ----
FROM docker.io/library/golang:1.25-bookworm AS builder
WORKDIR /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates gcc g++ libc6-dev && \
    rm -rf /var/lib/apt/lists/*

COPY services/user-service/go.mod services/user-service/go.sum ./
RUN go mod download

COPY services/user-service/ ./
COPY --from=proto-builder /gen/userv1/ ./gen/userv1/

RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -o /out/user-service ./cmd/user-service

# ---- Runtime stage ----
# cc-debian12 includes glibc (required by DuckDB/CGO), unlike static-debian12.
FROM gcr.io/distroless/cc-debian12:nonroot
WORKDIR /app

ENV PORT=50058
ENV DUCKDB_PATH=/data/user-service.duckdb

COPY --from=builder /out/user-service /app/user-service

EXPOSE 50058
ENTRYPOINT ["/app/user-service"]
