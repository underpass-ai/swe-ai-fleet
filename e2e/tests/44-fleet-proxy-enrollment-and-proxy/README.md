# E2E Test 44: Fleet-Proxy Enrollment + mTLS Validation

## Purpose

Validates the fleet-proxy security boundary end-to-end:

1. **API key enrollment** via `StaticKeyStore` (env-var-based, no Valkey needed)
2. **PKI certificate issuance** — CSR signed by internal CA
3. **mTLS handshake** with the issued client certificate
4. **Auth/authz interceptors** correctly pass authenticated requests
5. **Unauthenticated rejection** — requests without client cert are denied

## Prerequisites

- `fleet-proxy` deployed in `swe-ai-fleet` namespace
- `STATIC_API_KEYS` env var set (e.g. `e2e-key:e2e-secret:e2e-user:e2e-device`)
- cert-manager PKI secrets mounted (`fleet-proxy-server-tls`, `fleet-client-ca-secret`)

## Test Steps

| Step | Action | Success Criteria |
|------|--------|------------------|
| 0 | TCP connectivity to fleet-proxy:8443 | Connection succeeds |
| 1 | Generate ECDSA P-256 keypair + CSR | Key and CSR generated |
| 2 | Enroll via API key (TLS channel) | Receives signed client cert |
| 3 | Parse certificate: SPIFFE SAN, expiry, key usage | Valid cert structure |
| 4 | Create mTLS channel with issued cert | Channel ready |
| 5 | CreateProject via mTLS | INTERNAL (planning stub) = pass |
| 6 | ListProjects via mTLS | INTERNAL (planning stub) = pass |
| 7 | ListProjects without mTLS | UNAUTHENTICATED or UNAVAILABLE |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_PROXY_URL` | `fleet-proxy.swe-ai-fleet.svc.cluster.local:8443` | Target gRPC endpoint |
| `FLEET_PROXY_API_KEY` | `e2e-key:e2e-secret` | API key in `keyID:secret` format |
| `FLEET_PROXY_DEVICE_ID` | `e2e-device` | Device ID for enrollment |

## Usage

```bash
# Build image
make build

# Deploy to cluster
make deploy

# Check status
make status

# View logs
make logs

# Clean up
make delete
```
