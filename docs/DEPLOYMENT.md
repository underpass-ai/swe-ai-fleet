# Deployment Guide

EdgeCrew supports three common scenarios. Choose the one that matches your environment and scale.

## Workstation

- Single machine with 4×24 GB GPUs recommended (e.g., RTX 3090/4090)
- Rootless Podman/CRI-O or Docker
- Python 3.13 virtual environment

Steps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip && pip install -e .
python -m pytest tests/unit -v
```

## Homelab / Edge

- Single-node setup; container runtime required
- Optionally run Kubernetes (kind/k3s) to simulate cluster workflows

Suggested flow:

1. Prepare the Python environment (as above)
2. Validate with unit/integration tests
3. Use the E2E CLI to dry-run flows:

```bash
swe_ai_fleet-e2e --help
```

## Enterprise Cluster

- Kubernetes + Ray/KubeRay for horizontal scaling
- Integrate with your internal identity, artifact, and observability stack

High-level steps:

1. Provision a Kubernetes cluster with GPU workers (as needed)
2. Install base services via Helm (cluster controller, schedulers)
3. Configure namespaces, storage classes, network policies
4. Deploy EdgeCrew workloads and connect to your CI/CD

Notes:

- Keep secrets externalized and injected at runtime (e.g., sealed secrets)
- Enforce resource quotas and PodSecurity standards
- Prefer rootless runtimes and minimal base images

## Health checks and validation

- Unit tests: `python -m pytest tests/unit -v`
- Integration tests: `python -m pytest tests/integration -v`
- End-to-end (dry-run): `swe_ai_fleet-e2e --help`


