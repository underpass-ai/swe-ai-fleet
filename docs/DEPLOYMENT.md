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

## Ray (nativo, sin Kubernetes)

Ejecuta EdgeCrew sobre Ray local o en un clúster ligero sin K8s.

Prerequisitos:

- `pip install "ray[default]"`
- Puertos abiertos para dashboard (8265) si usas acceso remoto

Head local:

```bash
ray start --head --dashboard-host=0.0.0.0
ray status

# Job simple
ray job submit --address http://127.0.0.1:8265 -- python -c "print('hello from ray')"
```

Worker remoto (opcional):

```bash
ray start --address='ray://<HEAD_IP>:10001'  # o --address='<HEAD_IP>:6379' segun configuración
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


