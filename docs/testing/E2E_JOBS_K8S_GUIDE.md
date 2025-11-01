# E2E Tests on Kubernetes Jobs – Definitive Guide (2025)

Version: 1.0
Owner: SWE AI Fleet

---

## Purpose
This guide explains, end-to-end, how to port any existing/obsolete E2E test to run inside the Kubernetes cluster as a Job. Running inside the cluster provides direct access to internal services (`*.svc.cluster.local`) and the same environment as production.

---

## Standard Layout

```
jobs/test-<name>-e2e/
├── Dockerfile          # Python 3.13, grpcio, pytest or script runner
└── run_test.py         # Runner that builds stubs (if needed) and executes the test

deploy/k8s/
└── 99-test-<name>-e2e.yaml  # Job manifest with env, resources
```

---

## Porting Checklist (Obsolete → Job)

1) Identify test entrypoint
- If it is a pytest file: run via pytest.
- If it is a script with `asyncio.run(main())`: execute directly with `python file.py`.

2) Collect dependencies
- Python packages: grpcio, grpcio-tools, protobuf, pytest/pytest-asyncio if needed.
- Spec files: copy `specs/` into the image to generate stubs at runtime.

3) Generate gRPC stubs at runtime
- Use `grpc_tools.protoc` inside the runner or Dockerfile.
- Fix `_grpc.py` imports to package-relative (known protoc quirk).
- Ensure `PYTHONPATH=/app` (or workspace) and `gen/__init__.py` exists.

4) Use in-cluster FQDNs
- Example: `orchestrator.swe-ai-fleet.svc.cluster.local:50055`
- Example: `nats://nats.swe-ai-fleet.svc.cluster.local:4222`

5) Security and execution
- Non-root user (UID 1000).
- Reasonable resources (e.g., requests: 200m/512Mi; limits: 1 CPU/2Gi).
- `restartPolicy: Never` and TTL to auto-clean jobs.

6) Build and push
```bash
podman build -t registry.underpassai.com/swe-fleet/test-<name>-e2e:vX.Y.Z \
  -f jobs/test-<name>-e2e/Dockerfile .
podman push registry.underpassai.com/swe-fleet/test-<name>-e2e:vX.Y.Z
```

7) Apply and observe
```bash
kubectl delete job test-<name>-e2e -n swe-ai-fleet --ignore-not-found=true
kubectl apply -f deploy/k8s/99-test-<name>-e2e.yaml
kubectl logs -n swe-ai-fleet -l app.kubernetes.io/name=test-<name>-e2e -f
```

---

## Patterns

- Self-contained image (recommended): copy `specs/` and test file into the image; no init container.
- Init container (alternative): clone repo at runtime into an `emptyDir` volume; test container runs from that workspace.

---

## Example: System E2E as a Job

- Runner: `jobs/test-system-e2e/run_test.py`
  - Generates stubs into `/app/gen`.
  - Executes `tests/e2e/test_system_e2e.py` directly (script style).
- Image: `jobs/test-system-e2e/Dockerfile`
- Job: `deploy/k8s/99-test-system-e2e.yaml`

---

## Troubleshooting

- "No tests ran" → The file is a script; run with `python <file>.py` instead of pytest.
- Import errors for `gen.*` → Ensure stubs generated; fix `_grpc.py` imports; set `PYTHONPATH=/app`.
- Connection errors → verify service DNS, namespace, and ports; confirm pods are running.
- Image not pulled → push to `registry.underpassai.com/swe-fleet` and use that tag in the manifest.

---

## Maintenance

- Version images (`vX.Y.Z`) and bump in `99-test-<name>-e2e.yaml`.
- Keep specs and test files in sync with current proto contracts.
