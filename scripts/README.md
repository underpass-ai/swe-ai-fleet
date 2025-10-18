# Scripts - SWE AI Fleet

Utility scripts for development, deployment, and maintenance.

---

## 🚀 Deployment Scripts

### `rebuild-and-deploy.sh`

**Complete rebuild and deployment automation for all services.**

Rebuilds all Docker images with versioned proto APIs, pushes them to the registry, deploys to Kubernetes, and verifies the deployment.

**Usage**:
```bash
# Full rebuild and deploy (recommended)
./scripts/rebuild-and-deploy.sh

# Skip building, only push and deploy existing images
./scripts/rebuild-and-deploy.sh --skip-build

# Don't wait for rollout completion
./scripts/rebuild-and-deploy.sh --no-wait
```

**What it does**:
1. **Build** (5 services):
   - orchestrator (v2.2.1-api-versioned)
   - ray-executor (v2.1.1-api-versioned)
   - context (v1.1.1-api-versioned)
   - orchestrator-jobs (v1.1.1-api-versioned)
   - monitoring (v1.1.1-deliberations)

2. **Push** to `registry.underpassai.com/swe-ai-fleet/`

3. **Deploy** to Kubernetes namespace `swe-ai-fleet`

4. **Verify**:
   - Wait for rollout completion (120s timeout)
   - Check pod status
   - Detect crash loops
   - Report readiness

**Output**:
```
════════════════════════════════════════════════════════
  SWE AI Fleet - Rebuild & Redeploy
════════════════════════════════════════════════════════

▶ STEP 1/4: Building Docker images...
✓ Orchestrator built (v2.2.1-api-versioned)
✓ Ray-executor built (v2.1.1-api-versioned)
...
▶ STEP 4/4: Waiting for rollout completion...
✓ All pods are running without crash loops!
```

**Exit Codes**:
- `0`: Success
- `1`: Build/push/deploy failure

---

## 🛠️ Tooling Scripts

### `install-buf.sh`

Installs Buf CLI tool for proto validation and linting.

**Usage**:
```bash
./scripts/install-buf.sh

# Custom install directory
INSTALL_DIR=~/.local/bin ./scripts/install-buf.sh
```

**What it installs**:
- Buf v1.40.1
- Platform: Linux/Darwin (x86_64/aarch64)
- Location: `/usr/local/bin/buf` or custom `$INSTALL_DIR`

---

## 🧪 Testing Scripts

### `ci-test-with-grpc-gen.sh`

Generates gRPC stubs and runs tests (used in CI).

**Usage**:
```bash
./scripts/ci-test-with-grpc-gen.sh
```

**What it does**:
1. Activates virtual environment
2. Generates gRPC Python stubs from protos
3. Runs pytest with coverage

---

## 📝 Script Conventions

### Naming
- `verb-noun.sh` format (e.g., `rebuild-and-deploy.sh`)
- Lowercase with hyphens
- Descriptive, self-explanatory names

### Structure
All scripts follow this pattern:
```bash
#!/bin/bash
set -e  # Exit on error

# Configuration (paths, versions, etc.)
# Colors and logging functions
# Argument parsing
# Main logic with clear steps
# Error handling and verification
# User-friendly output
```

### Error Handling
- Use `set -e` to exit on errors
- Validate prerequisites
- Provide clear error messages
- Exit codes: 0 (success), 1 (failure)

### Output
- Use colors for better readability
- Progress indicators (ℹ, ✓, ✗, ⚠, ▶)
- Clear step separation
- Summary at the end

---

## 🔍 Troubleshooting

### Script Not Executable
```bash
chmod +x scripts/<script-name>.sh
```

### Permission Denied
```bash
# For Buf installation
sudo ./scripts/install-buf.sh
# or
INSTALL_DIR=~/.local/bin ./scripts/install-buf.sh
```

### Build Failures
Check Docker/Podman is running:
```bash
podman ps
```

### Deploy Failures
Check kubectl context:
```bash
kubectl config current-context
kubectl get nodes
```

---

## 📚 Related Documentation

- [API Versioning Strategy](../docs/API_VERSIONING_STRATEGY.md)
- [Tooling Setup](../docs/TOOLING_SETUP.md)
- [Microservices Build Patterns](../docs/MICROSERVICES_BUILD_PATTERNS.md)

---

Last Updated: 2025-10-18

