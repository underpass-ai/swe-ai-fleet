# syntax=docker/dockerfile:1.7

# ---- Proto generation stage ----
FROM docker.io/library/golang:1.25-alpine AS proto-builder
RUN apk add --no-cache protobuf
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /proto
COPY specs/fleet/proxy/v1/fleet_proxy.proto /proto/fleet_proxy.proto

RUN mkdir -p /gen/proxyv1 && \
    protoc -I/proto \
    --go_out=/gen/proxyv1 --go_opt=paths=source_relative \
    --go-grpc_out=/gen/proxyv1 --go-grpc_opt=paths=source_relative \
    fleet_proxy.proto

# ---- Build stage ----
FROM docker.io/library/golang:1.25-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY tools/fleetctl/go.mod tools/fleetctl/go.sum ./
RUN go mod download

COPY tools/fleetctl/ ./
COPY --from=proto-builder /gen/proxyv1/ ./gen/proxyv1/

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "-X main.version=docker" -o /out/fleetctl ./cmd/fleetctl

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app

COPY --from=builder /out/fleetctl /app/fleetctl

ENTRYPOINT ["/app/fleetctl"]
