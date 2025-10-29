# E2E Tests Migration Guide - Kubernetes Jobs

Version: 1.0
Date: 2025-01-28
Status: ✅ Implemented and validated

---

## Executive Summary

This guide explains how to migrate E2E tests from local execution to Kubernetes Jobs that run inside the cluster. Running inside the cluster allows tests to reach internal services (`*.svc.cluster.local`) without port-forwarding or special network setup.

---

## Why Migrate

### Before (Local Execution)
- ❌ Tests cannot access internal K8s services directly
- ❌ Requires manual port-forwarding per service
- ❌ Complex, error-prone networking setup
- ❌ Environment differences vs production

### After (Kubernetes Jobs)
- ✅ Tests run inside the cluster
- ✅ Direct access via internal DNS
- ✅ Same environment as production
- ✅ No manual networking
- ✅ Isolated and reproducible execution

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (namespace: swe-ai-fleet)            │
│                                                          │
│  ┌──────────────────────────────────────────────┐       │
│  │  Init Container (alpine/git)                  │       │
│  │  - Clone repo from GitHub                     │       │
│  │  - Fix permissions (UID 1000)                 │       │
│  └──────────────────────────────────────────────┘       │
│                        ↓                                 │
│  ┌──────────────────────────────────────────────┐       │
│  │  Test Container                               │       │
│  │  - Install dependencies                       │       │
│  │  - Run pytest                                 │       │
│  │  - Access internal services                   │       │
│  │    • vllm-server:8000                         │       │
│  │    • orchestrator:50055                       │       │
│  │    • context:50054                            │       │
│  └──────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## Standard E2E Job Layout

Each E2E test follows this structure:

```
jobs/test-<name>-e2e/
├── Dockerfile          # Image with pytest and dependencies
└── run_test.py         # Script to run the specific test

deploy/k8s/
└── 99-test-<name>-e2e.yaml  # Kubernetes Job manifest
```

---

## Step-by-Step: Create a New E2E Job

### 1) Create the job directory

```bash
mkdir -p jobs/test-<name>-e2e
```

### 2) Create the Dockerfile

File: `jobs/test-<name>-e2e/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for E2E testing
RUN pip install --no-cache-dir \
    pytest==8.4.2 \
    pytest-asyncio==0.25.2 \
    pytest-mock==3.14.0 \
    pytest-cov==5.0.0 \
    aiohttp>=3.9.0 \
    pyyaml>=6.0 \
    pydantic>=2.0.0 \
    requests \
    psycopg2-binary

# Create non-root user with home directory
RUN groupadd -r jobuser && \
    useradd -r -m -g jobuser -u 1000 jobuser && \
    mkdir -p /workspace && \
    chown -R jobuser:jobuser /app /workspace

# Copy test runner script
COPY jobs/test-<name>-e2e/run_test.py /app/run_test.py

# Set working directory to workspace (where repo will be cloned)
WORKDIR /workspace

# Switch to non-root user
USER jobuser

# Configure git for the test user
RUN git config --global user.name "E2E Test Agent" && \
    git config --global user.email "e2e@swe-ai-fleet.local" && \
    git config --global init.defaultBranch main

# Default: run the test runner script
CMD ["python", "/app/run_test.py"]
```

Key points:
- ✅ Uses Python 3.13-slim (lightweight)
- ✅ Installs pytest and required libs
- ✅ Non-root user (UID 1000)
- ✅ Git configured for commits if needed
- ✅ Entrypoint script at `/app/run_test.py`

### 3) Create the test runner script

File: `jobs/test-<name>-e2e/run_test.py`

```python
#!/usr/bin/env python3
"""
E2E Test Runner for <Test Name>.

Runs the specific test inside the Kubernetes cluster
where it can access services via cluster DNS.
"""

import os
import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def main():
    """Run the E2E test."""
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🚀 <Name> E2E Test{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print()

    # Check if workspace exists (should be cloned by init container)
    workspace = Path("/workspace")
    if not workspace.exists():
        print(f"{RED}❌ Workspace directory not found at /workspace{RESET}")
        print("   Make sure init container cloned the repository")
        sys.exit(1)

    print(f"{GREEN}✓ Workspace found at {workspace}{RESET}")
    print()

    # Change to workspace directory
    os.chdir(workspace)

    # Check if this is a git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()
        print(f"{GREEN}✓ Repository at commit: {commit}{RESET}")
    except subprocess.CalledProcessError:
        print(f"{YELLOW}⚠️  Not a git repository (might be OK if copied differently){RESET}")

    print()

    # Display environment
    print(f"{BLUE}Environment Configuration:{RESET}")
    vllm_url = os.getenv("VLLM_URL", "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000")
    orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")

    print(f"  VLLM_URL: {vllm_url}")
    print(f"  ORCHESTRATOR_HOST: {orchestrator_host}")
    print()

    # Install project dependencies
    print(f"{BLUE}📦 Installing project dependencies...{RESET}")
    try:
        subprocess.run(
            ["pip", "install", "--user", "-q", "-e", ".[dev,grpc]"],
            check=True,
            cwd=workspace,
        )
        print(f"{GREEN}✓ Dependencies installed{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}❌ Failed to install dependencies: {e}{RESET}")
        sys.exit(1)

    print()

    # Run the specific test(s)
    print(f"{BLUE}🧪 Running E2E test: <test_name>{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print()

    # Point to your specific test
    test_path = "tests/e2e/<path>/test_<file>.py::test_<name>"

    # Run pytest
    try:
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                test_path,
                "-v",
                "-s",
                "--tb=short",
            ],
            cwd=workspace,
        )

        exit_code = result.returncode

        print()
        print(f"{BLUE}{'='*70}{RESET}")
        if exit_code == 0:
            print(f"{GREEN}✅ Test PASSED!{RESET}")
        else:
            print(f"{RED}❌ Test FAILED with exit code {exit_code}{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")

        sys.exit(exit_code)

    except Exception as e:
        print(f"{RED}❌ Error running test: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Key points:
- ✅ Validates workspace exists
- ✅ Prints environment
- ✅ Installs project dependencies
- ✅ Runs specific pytest target
- ✅ Clear exit codes

### 4) Create the Kubernetes Job manifest

File: `deploy/k8s/99-test-<name>-e2e.yaml`

```yaml
---
# Kubernetes Job to run <Name> E2E test in cluster
apiVersion: batch/v1
kind: Job
metadata:
  name: test-<name>-e2e
  namespace: swe-ai-fleet
  labels:
    app: test-<name>-e2e
    component: e2e-test
spec:
  ttlSecondsAfterFinished: 3600  # Keep for 1 hour after completion
  backoffLimit: 0  # Don't retry on failure
  template:
    metadata:
      labels:
        app: test-<name>-e2e
        component: e2e-test
    spec:
      restartPolicy: Never
      securityContext:
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: test-runner
          # Use pre-built test image
          image: registry.underpassai.com/swe-fleet/test-<name>-e2e:v0.1.0
          imagePullPolicy: Always
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: false
            runAsNonRoot: true
            runAsUser: 1000
            capabilities:
              drop:
                - ALL
          command: ["python", "/app/run_test.py"]

          workingDir: /workspace

          volumeMounts:
            - name: source-code
              mountPath: /workspace
              readOnly: false

          resources:
            requests:
              cpu: "500m"
              memory: "2Gi"
            limits:
              cpu: "2000m"
              memory: "4Gi"

          env:
            - name: PYTHONUNBUFFERED
              value: "1"
            - name: PYTEST_CURRENT_TEST
              value: ""
            # Cluster service endpoints
            - name: VLLM_URL
              value: "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000"
            - name: ORCHESTRATOR_HOST
              value: "orchestrator.swe-ai-fleet.svc.cluster.local"
            - name: ORCHESTRATOR_PORT
              value: "50055"
            - name: CONTEXT_HOST
              value: "context.swe-ai-fleet.svc.cluster.local"
            - name: CONTEXT_PORT
              value: "50054"

      volumes:
        - name: source-code
          emptyDir: {}

      initContainers:
        - name: clone-repo
          image: docker.io/alpine/git:v2.43.0
          command:
            - /bin/sh
            - -c
            - |
              set -e
              echo "📥 Cloning repository..."

              # Try to clone from current branch if possible, otherwise main
              BRANCH="${GIT_BRANCH:-main}"
              git clone --depth 1 --branch "${BRANCH}" https://github.com/underpass-ai/swe-ai-fleet.git /workspace 2>/dev/null || \
              git clone --depth 1 https://github.com/underpass-ai/swe-ai-fleet.git /workspace

              cd /workspace

              # Fix permissions for agent user (UID 1000)
              chown -R 1000:1000 /workspace

              echo "✓ Repository cloned and permissions fixed"
              echo "✓ Branch/commit: $(git rev-parse --short HEAD)"
          volumeMounts:
            - name: source-code
              mountPath: /workspace
          securityContext:
            runAsUser: 0
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
              add:
                - CHOWN
          env:
            - name: GIT_BRANCH
              value: "hexagonal-refactor-v2"  # Set to current or main

---
# Service Account for the test job
apiVersion: v1
kind: ServiceAccount
metadata:
  name: test-<name>-e2e
  namespace: swe-ai-fleet
  labels:
    app: test-<name>-e2e

---
# Role for test job (minimal permissions - read pods for debugging)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: test-<name>-e2e
  namespace: swe-ai-fleet
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list"]

---
# RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: test-<name>-e2e
  namespace: swe-ai-fleet
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: test-<name>-e2e
subjects:
  - kind: ServiceAccount
    name: test-<name>-e2e
    namespace: swe-ai-fleet
```

Key points:
- ✅ Init container clones repo from GitHub
- ✅ Test container runs the script
- ✅ Environment variables point to cluster services
- ✅ Minimal ServiceAccount permissions
- ✅ Resource requests/limits appropriate to the test

---

## Build and Run Workflow

### 1) Build the image

```bash
cd /home/tirso/ai/developents/swe-ai-fleet

podman build -t registry.underpassai.com/swe-fleet/test-<name>-e2e:v0.1.0 \
  -f jobs/test-<name>-e2e/Dockerfile .
```

### 2) Push to registry

```bash
podman push registry.underpassai.com/swe-fleet/test-<name>-e2e:v0.1.0
```

### 3) Clean previous job (if any)

```bash
kubectl delete job test-<name>-e2e -n swe-ai-fleet --ignore-not-found=true
```

### 4) Apply the job

```bash
kubectl apply -f deploy/k8s/99-test-<name>-e2e.yaml
```

### 5) Wait and stream logs

```bash
# Wait for pod ready
kubectl wait --for=condition=Ready pod -l app=test-<name>-e2e -n swe-ai-fleet --timeout=120s

# Stream logs
kubectl logs -f -n swe-ai-fleet -l app=test-<name>-e2e

# Job status
kubectl get job test-<name>-e2e -n swe-ai-fleet
```

### 6) Verify result

```bash
# Final job status
kubectl get job test-<name>-e2e -n swe-ai-fleet

# Tail logs on failure
kubectl logs -n swe-ai-fleet -l app=test-<name>-e2e --tail=100
```

---

## Migration Checklist

To migrate an existing E2E test to this method:

- [ ] Create `jobs/test-<name>-e2e/`
- [ ] Create `Dockerfile` with required deps
- [ ] Create `run_test.py` to run the specific test
- [ ] Create `deploy/k8s/99-test-<name>-e2e.yaml`
- [ ] Build and push the image
- [ ] Apply job and verify
- [ ] Update documentation as needed
- [ ] (Optional) Add helper script for quick runs

---

## Real Example: test-vllm-agent-tools-e2e

### Layout
```
jobs/test-vllm-agent-tools-e2e/
├── Dockerfile
└── run_test.py

deploy/k8s/
└── 99-test-vllm-agent-tools-e2e.yaml
```

### Test
- Test: `test_vllm-agent_with_smart_context`
- File: `tests/e2e/orchestrator/test_orchestrator_with_tools_e2e.py`
- Result: ✅ PASSED (0.59s)

### Commands

```bash
# Build
podman build -t registry.underpassai.com/swe-fleet/test-vllm-agent-tools-e2e:v0.1.0 \
  -f jobs/test-vllm-agent-tools-e2e/Dockerfile .

# Push
podman push registry.underpassai.com/swe-fleet/test-vllm-agent-tools-e2e:v0.1.0

# Deploy
kubectl delete job test-vllm-agent-tools-e2e -n swe-ai-fleet --ignore-not-found=true
kubectl apply -f deploy/k8s/99-test-vllm-agent-tools-e2e.yaml

# Watch
kubectl logs -f -n swe-ai-fleet -l app=test-vllm-agent-tools-e2e
```

---

## Troubleshooting

### Issue: Pod won't start
```bash
# Inspect pod events
kubectl describe pod -l app=test-<name>-e2e -n swe-ai-fleet

# View init container logs
kubectl logs -n swe-ai-fleet <pod-name> -c clone-repo
```

### Issue: Image not found
```bash
# Verify image exists locally
podman images | grep test-<name>-e2e

# Verify registry access from cluster
kubectl run test-pull --image=registry.underpassai.com/swe-fleet/test-<name>-e2e:v0.1.0 --dry-run=client -o yaml
```

### Issue: Connection errors in test
```bash
# Verify services
kubectl get svc -n swe-ai-fleet | grep -E "vllm|orchestrator|context"

# Check DNS from inside the pod
kubectl exec -n swe-ai-fleet <pod-name> -- nslookup vllm-server.swe-ai-fleet.svc.cluster.local
```

### Issue: Permission denied
```bash
# Verify ServiceAccount binding
kubectl get rolebinding test-<name>-e2e -n swe-ai-fleet -o yaml

# Verify pod uses expected ServiceAccount
kubectl get pod -l app=test-<name>-e2e -n swe-ai-fleet -o jsonpath='{.items[0].spec.serviceAccountName}'
```

---

## Benefits Summary

| Aspect | Local | K8s Job |
|--------|-------|---------|
| Service access | ❌ Port-forwarding | ✅ Internal DNS |
| Environment | ❌ Differs from prod | ✅ Matches prod |
| Isolation | ❌ Shared resources | ✅ Container isolated |
| Reproducibility | ⚠️ Machine-dependent | ✅ Consistent |
| Debugging | ✅ Easy local tools | ⚠️ Requires kubectl |
| CI/CD | ⚠️ Extra config | ✅ Natural integration |

---

## Next Steps

1. Migrate remaining tests:
   - `test_full_architecture_deliberation`
   - Others under `tests/e2e/orchestrator/`
   - Tests under `tests/e2e/context/`

2. Create a helper script:
   ```bash
   scripts/test/run-e2e-job.sh <test-name>
   ```

3. Integrate into CI/CD:
   - Automatic trigger after push
   - Notifications
   - Auto-retry on failures

4. Improve logging:
   - Add timestamps
   - Structured JSON logs
   - Centralized log collection

---

## References

- Example job: `jobs/test-vllm-agent-tools-e2e/`
- Manifest: `deploy/k8s/99-test-vllm-agent-tools-e2e.yaml`
- Original test: `tests/e2e/orchestrator/test_orchestrator_with_tools_e2e.py`
- Other jobs: `jobs/orchestrator/`, `jobs/deliberation/`

---

Last Updated: 2025-01-28
Author: Documentation generated during E2E tests migration

