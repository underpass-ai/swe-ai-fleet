# Fleet Proxy (BFF)

gRPC/mTLS Backend-for-Frontend that runs in-cluster and multiplexes CLI requests
to internal services (Planning, Ceremony Processor, NATS JetStream).

## Architecture

- Transport: gRPC over mTLS (port 8443)
- Authentication: SPIFFE-based client certificates (short-lived, 24h)
- Authorization: role-based (Viewer, Operator, Admin) per RPC method
- Event streaming: NATS JetStream server-streaming to clients
- Pattern: hexagonal + DDD + CQRS

## gRPC Services

### EnrollmentService (TLS, no client cert required for Enroll)

- `Enroll` - Exchange API key for client certificate
- `Renew` - Renew certificate using existing mTLS identity

### FleetCommandService (mTLS required)

- `CreateProject`, `CreateEpic`, `CreateStory`, `TransitionStory`
- `CreateTask`
- `StartPlanningCeremony`, `StartBacklogReview`
- `ApproveDecision`, `RejectDecision`

### FleetQueryService (mTLS required)

- `ListProjects`, `ListEpics`, `ListStories`, `ListTasks`
- `GetCeremonyInstance`, `ListCeremonyInstances`
- `WatchEvents` (server-streaming real-time event feed)

## PKI / mTLS

Certificates are managed via cert-manager:

- **Server cert**: `fleet-proxy-server-tls` (DNS SAN: `fleet-proxy.swe-ai-fleet.svc.cluster.local`)
- **Client CA**: `fleet-client-ca-secret` (self-signed CA, signs client certs)
- **Client certs**: 24h TTL, SPIFFE URI SAN (`spiffe://swe-ai-fleet/user/{userId}/device/{deviceId}`)

Enrollment flow:

1. Operator calls `Enroll` with an API key (TLS only, no client cert)
2. Proxy validates key, signs CSR with CA, returns client cert + CA chain
3. All subsequent calls use mTLS with the issued client cert

## Environment Variables

- `PORT` (default: `8443`)
- `TLS_CERT_PATH` - Server certificate PEM
- `TLS_KEY_PATH` - Server private key PEM
- `CLIENT_CA_CERT_PATH` - Client CA certificate PEM (for mTLS verification)
- `CA_CERT_PATH` - CA cert for signing client certs
- `CA_KEY_PATH` - CA private key for signing client certs
- `PLANNING_SERVICE_ADDR` (default: `localhost:50051`)
- `CEREMONY_SERVICE_ADDR` (default: `localhost:50052`)
- `NATS_URL` (default: `nats://localhost:4222`)
- `VALKEY_ADDR` (default: `localhost:6379`)
- `RATE_LIMIT_RPS` (default: `100`, per-identity token bucket)

When TLS paths are not set, the server starts in insecure mode (development only).

## Run

```bash
make run
```

Or directly:

```bash
go run ./cmd/fleet-proxy
```

## Build

```bash
make build          # Binary at bin/fleet-proxy
make docker-build   # Container image
```

## Tests

```bash
make test           # All tests
make coverage-core  # Core coverage gate (80% on domain + app layers)
make coverage-full  # Full coverage for SonarCloud
```

Core test packages: `./internal/app/... ./internal/domain/...`

## Deploy

```bash
# 1. Deploy PKI resources
kubectl apply -f deploy/k8s/30-microservices/fleet-proxy-pki.yaml

# 2. Deploy service
kubectl apply -f deploy/k8s/30-microservices/fleet-proxy.yaml

# 3. Port-forward for local access
kubectl port-forward -n swe-ai-fleet svc/fleet-proxy 8443:8443
```

## Project Structure

```
services/fleet-proxy/
├── cmd/fleet-proxy/       # Entry point
├── internal/
│   ├── domain/            # Pure domain (no infra imports)
│   │   ├── identity/      # ClientID, ApiKeyID, CertFingerprint, SANUri, Role
│   │   ├── auth/          # Scope, Enrollment, ClientCertificate, AuthorizationPolicy
│   │   └── event/         # FleetEvent, EventType, EventFilter
│   ├── app/               # Application layer
│   │   ├── command/       # CQRS write-side handlers
│   │   ├── query/         # CQRS read-side handlers
│   │   └── ports/         # Outbound port interfaces
│   └── adapters/          # Infrastructure implementations
│       ├── grpcapi/       # Inbound: gRPC server + interceptors
│       ├── planning/      # Outbound: Planning Service client
│       ├── ceremony/      # Outbound: Ceremony Processor client
│       ├── nats/          # Outbound: NATS JetStream subscriber
│       ├── pki/           # Outbound: CA certificate signing
│       ├── keystore/      # Outbound: API key validation (Valkey)
│       ├── identitymap/   # Outbound: identity-to-role mapping
│       └── audit/         # Outbound: structured audit logs
├── Makefile
├── Dockerfile
├── go.mod
└── go.sum
```
