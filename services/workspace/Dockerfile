# syntax=docker/dockerfile:1.7

FROM docker.io/library/golang:1.23-alpine AS builder
WORKDIR /src

RUN apk add --no-cache git ca-certificates

COPY services/workspace/go.mod ./go.mod
RUN go mod download

COPY services/workspace/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/workspace-service ./cmd/workspace

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app

ENV PORT=50053
ENV WORKSPACE_ROOT=/tmp/swe-workspaces
ENV ARTIFACT_ROOT=/tmp/swe-artifacts

COPY --from=builder /out/workspace-service /app/workspace-service

EXPOSE 50053
ENTRYPOINT ["/app/workspace-service"]
