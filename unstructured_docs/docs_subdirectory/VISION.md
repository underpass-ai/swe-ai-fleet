# Vision — EdgeCrew

EdgeCrew is the **reference architecture** for multi-agent agile engineering.

## Mission
Create the first open-source industry reference for multi-agent agile engineering, making autonomous software squads trustworthy, auditable, and efficient.

## Differentiators
- Agile squad simulation with role-based agents.
- Human as Product Owner (no PM bot).
- Automated role-context pipelines.
- Memory hybrid: in-memory short-term + graph long-term.
- Deployment: workstation (2×24 GB minimum, 4–8×24 GB recommended), native Ray (no Kubernetes), or enterprise cluster (KubeRay, multi‑node ≥1×24 GB per node).

## Roadmap
- M1: Agile multi‑agent E2E (human PO, roles, memory, and auditability).
- M2: Knowledge graph memory & user story lifecycle.
- M3: Advanced validators and QA suite.
- M4: Enterprise-ready Helm charts, CI/CD integration.

Legacy PoC:
- Cluster-from-YAML (legacy, demo only). See `examples/cluster_from_yaml/`.
