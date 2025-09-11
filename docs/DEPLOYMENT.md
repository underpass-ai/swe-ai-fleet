# Deployment Guide

EdgeCrew supports three common scenarios. Choose the one that matches your environment and scale.

## Workstation

- Single machine baseline: 2×24 GB GPUs (dev/test). Recommended: 4–8×24 GB for production‑like throughput
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

## Ray (native, no Kubernetes)

Run EdgeCrew on local Ray or a lightweight cluster without Kubernetes.

Prerequisitos:

- `pip install "ray[default]"`
- Puertos abiertos para dashboard (8265) si usas acceso remoto

Local head:

```bash
ray start --head --dashboard-host=0.0.0.0
ray status

# Job simple
ray job submit --address http://127.0.0.1:8265 -- python -c "print('hello from ray')"
```

Remote worker (optional):

```bash
ray start --address='ray://<HEAD_IP>:10001'  # or --address='<HEAD_IP>:6379' depending on setup
```

## Enterprise Cluster

- Kubernetes + Ray/KubeRay for horizontal scaling (multi‑node, cada nodo ≥1×24 GB)
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

## Why CRI-O instead of Docker (for this project)

EdgeCrew prioriza CRI-O por su alineación con Kubernetes, seguridad y soporte CDI para GPUs:

- Seguridad y aislamiento:
  - CRI-O sigue de cerca el stack de contenedores de Kubernetes (OCI runtime + runc/crun), con menor superficie y sin daemon privilegiado único.
  - Integración natural con políticas Pod/RuntimeClass y SELinux/AppArmor.
- Compatibilidad con GPU (NVIDIA CDI):
  - Integración directa con NVIDIA Container Toolkit vía CDI (device injection declarativa), el mismo mecanismo que se usa en Kubernetes.
  - Menos dependencia de banderas ad‑hoc; el runtime `nvidia` se selecciona por handler.
- Paridad con clústeres:
  - Lo que validas en local (CRI-O + CDI + hostNetwork) es muy similar a cómo funcionará en K8s con RuntimeClass y KubeRay.
- Observabilidad y trazabilidad:
  - Herramientas familiares (`crictl`, `journalctl`) para depuración de bajo nivel.
- Rendimiento y footprint:
  - Menor overhead de daemon y buen comportamiento rootless con Podman para flujos de desarrollo.

Docker sigue siendo compatible, pero para escenarios con GPU y una ruta clara hacia Kubernetes/Ray, CRI-O reduce sorpresas y simplifica el hardening.


