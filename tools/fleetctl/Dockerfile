# syntax=docker/dockerfile:1.7

FROM docker.io/library/golang:1.23-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY tools/fleetctl/go.mod tools/fleetctl/go.sum ./
RUN go mod download

COPY tools/fleetctl/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "-X main.version=docker" -o /out/fleetctl ./cmd/fleetctl

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app

COPY --from=builder /out/fleetctl /app/fleetctl

ENTRYPOINT ["/app/fleetctl"]
