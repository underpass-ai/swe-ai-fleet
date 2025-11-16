# Security & Privacy

EdgeCrew is designed with a local-first and auditable mindset.

## Principles

- Least privilege: limit permissions for agents and runtimes
- Isolation: containerized execution, ephemeral workspaces
- Auditability: structured logs and decision trails
- Data minimization: only necessary context is shared per role
- Offline-capable: can run without external APIs

## Secrets

- Inject at runtime via environment or secret stores
- Avoid hardcoding in code or configs
- Rotate regularly; prefer short-lived tokens

## Runtime hardening

- CRI‑O (host networking for demo; network policies in K8s)
- CPU/memory limits, timeouts, and network policies
- Read-only filesystems where possible; dedicated workspace mounts

## Privacy

- Role-based context gating prevents overexposure of information
- Summaries redact sensitive data where appropriate
- Long-term storage is structured for traceability and access control

## Audit trails

- Capture: task metadata, decisions, artifacts, results
- Retain according to your org policy; enable immutability where required


