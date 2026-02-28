# syntax=docker/dockerfile:1.7

# ---- Proto generation stage ----
FROM docker.io/library/golang:1.24-alpine AS proto-builder
RUN apk add --no-cache protobuf
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /proto
COPY specs/fleet/planning/v2/planning.proto /proto/planning.proto
COPY specs/fleet/user/v1/user.proto /proto/user.proto

RUN mkdir -p /gen/planningv2 && \
    protoc -I/proto \
    --go_out=/gen/planningv2 --go_opt=paths=source_relative \
    --go-grpc_out=/gen/planningv2 --go-grpc_opt=paths=source_relative \
    planning.proto

RUN mkdir -p /gen/userv1 && \
    protoc -I/proto \
    --go_out=/gen/userv1 --go_opt=paths=source_relative \
    --go-grpc_out=/gen/userv1 --go-grpc_opt=paths=source_relative \
    user.proto

# ---- Build stage ----
FROM docker.io/library/golang:1.24-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY services/fleet-proxy/go.mod services/fleet-proxy/go.sum ./
RUN go mod download

COPY services/fleet-proxy/ ./
COPY --from=proto-builder /gen/planningv2/ ./gen/planningv2/
COPY --from=proto-builder /gen/userv1/ ./gen/userv1/

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/fleet-proxy ./cmd/fleet-proxy

# ---- Runtime stage ----
FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app

ENV PORT=8443

COPY --from=builder /out/fleet-proxy /app/fleet-proxy

EXPOSE 8443
ENTRYPOINT ["/app/fleet-proxy"]
