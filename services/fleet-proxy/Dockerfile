# syntax=docker/dockerfile:1.7

FROM docker.io/library/golang:1.24-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY services/fleet-proxy/go.mod services/fleet-proxy/go.sum ./
RUN go mod download

COPY services/fleet-proxy/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/fleet-proxy ./cmd/fleet-proxy

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app

ENV PORT=8443

COPY --from=builder /out/fleet-proxy /app/fleet-proxy

EXPOSE 8443
ENTRYPOINT ["/app/fleet-proxy"]
