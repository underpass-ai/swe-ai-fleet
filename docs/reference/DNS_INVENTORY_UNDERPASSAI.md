# DNS Inventory - underpassai.com

Date: 2026-02-22
Scope: DNS inventory for `underpassai.com` and private cluster DNS references.

## Active Ingress Hosts (Cluster)

| Namespace | Ingress | Host | Class |
|---|---|---|---|
| `container-registry` | `docker-registry` | `registry.underpassai.com` | `nginx` |
| `default` | `echo` | `echo.underpassai.com` | `nginx` |
| `swe-ai-fleet` | `monitoring-dashboard` | `monitoring-dashboard.underpassai.com` | `nginx` |
| `swe-ai-fleet` | `minio-workspace-ingress` | `minio-console.underpassai.com` | `nginx` |
| `swe-ai-fleet` | `planning-ui-ingress` | `planning.underpassai.com` | `nginx` |

## Route53 Record Inventory (Sanitized)

| Name | Type |
|---|---|
| `underpassai.com` | `A` |
| `underpassai.com` | `MX` |
| `underpassai.com` | `NS` |
| `underpassai.com` | `SOA` |
| `underpassai.com` | `TXT` |
| `_amazonses.underpassai.com` | `TXT` |
| `_dmarc.underpassai.com` | `TXT` |
| `es26fe4qf2k235ycrjjnxpq4o54xjyuj._domainkey.underpassai.com` | `CNAME` |
| `q36o7yj5sqkjgc7rofxkbs56qsadjyfc._domainkey.underpassai.com` | `CNAME` |
| `qoxfssl6vxp2wjbrqvni3d4doocm5ycg._domainkey.underpassai.com` | `CNAME` |
| `autodiscover.underpassai.com` | `CNAME` |
| `echo.underpassai.com` | `A` |
| `grpcui-context.underpassai.com` | `A` |
| `grpcui-rayexecutor.underpassai.com` | `A` |
| `grpcui.underpassai.com` | `A` |
| `minio-console.underpassai.com` | `A` |
| `monitoring-dashboard.underpassai.com` | `A` |
| `nats.underpassai.com` | `A` |
| `planning.underpassai.com` | `A` |
| `proto-docs.underpassai.com` | `A` |
| `registry.underpassai.com` | `A` |
| `grafana.swe-ai-fleet.underpassai.com` | `A` |
| `swe-fleet.underpassai.com` | `A` |
| `webui.underpassai.com` | `A` |

## Public FQDNs Currently Mapped to Private Network Targets

- `echo.underpassai.com`
- `grpcui-context.underpassai.com`
- `grpcui-rayexecutor.underpassai.com`
- `grpcui.underpassai.com`
- `minio-console.underpassai.com`
- `monitoring-dashboard.underpassai.com`
- `nats.underpassai.com`
- `planning.underpassai.com`
- `proto-docs.underpassai.com`
- `registry.underpassai.com`
- `grafana.swe-ai-fleet.underpassai.com`
- `swe-fleet.underpassai.com`
- `webui.underpassai.com`

## Private Cluster Internal DNS (`*.svc.cluster.local`)

Namespace: `swe-ai-fleet`

- `context.swe-ai-fleet.svc.cluster.local`
- `e2e-kafka.swe-ai-fleet.svc.cluster.local`
- `e2e-mongodb.swe-ai-fleet.svc.cluster.local`
- `e2e-nats.swe-ai-fleet.svc.cluster.local`
- `e2e-postgres.swe-ai-fleet.svc.cluster.local`
- `e2e-rabbitmq.swe-ai-fleet.svc.cluster.local`
- `grafana.swe-ai-fleet.svc.cluster.local`
- `internal-context.swe-ai-fleet.svc.cluster.local`
- `internal-nats.swe-ai-fleet.svc.cluster.local`
- `internal-neo4j.swe-ai-fleet.svc.cluster.local`
- `internal-planning.swe-ai-fleet.svc.cluster.local`
- `internal-registry.swe-ai-fleet.svc.cluster.local`
- `internal-storycoach.swe-ai-fleet.svc.cluster.local`
- `internal-valkey.swe-ai-fleet.svc.cluster.local`
- `internal-workspace.swe-ai-fleet.svc.cluster.local`
- `loki.swe-ai-fleet.svc.cluster.local`
- `minio-workspace-console-svc.swe-ai-fleet.svc.cluster.local`
- `minio-workspace-svc.swe-ai-fleet.svc.cluster.local`
- `nats.swe-ai-fleet.svc.cluster.local`
- `neo4j.swe-ai-fleet.svc.cluster.local`
- `orchestrator.swe-ai-fleet.svc.cluster.local`
- `planning.swe-ai-fleet.svc.cluster.local`
- `planning-ceremony-processor.swe-ai-fleet.svc.cluster.local`
- `planning-ui.swe-ai-fleet.svc.cluster.local`
- `ray-executor.swe-ai-fleet.svc.cluster.local`
- `redis.swe-ai-fleet.svc.cluster.local`
- `valkey.swe-ai-fleet.svc.cluster.local`
- `vllm-server-service.swe-ai-fleet.svc.cluster.local`
- `workflow.swe-ai-fleet.svc.cluster.local`
- `workspace.swe-ai-fleet.svc.cluster.local`
- `workspace-toolchains-e2e.swe-ai-fleet.svc.cluster.local`

## Sanitization Policy

- No account identifiers.
- No IP addresses.
- No TXT token values, MX values, NS values, or certificate metadata.
- Inventory keeps only hostnames, record types, and functional classification.
