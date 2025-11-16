# Tooling Setup - SWE AI Fleet

This document describes how to install and configure the development tools used in the SWE AI Fleet project.

---

## 🛠️ Required Tools

### 1. Buf - Protocol Buffer Toolkit

**What is Buf?**
- Industry-standard tool for working with Protocol Buffers
- Provides linting, breaking change detection, and code generation
- Used for API versioning and validation

**Installation**:

```bash
# Quick install (Linux/Mac)
./scripts/install-buf.sh

# Custom install directory
INSTALL_DIR=~/.local/bin ./scripts/install-buf.sh

# Manual download (if script fails)
BUF_VERSION=1.40.1
curl -sSL \
  "https://github.com/bufbuild/buf/releases/download/v${BUF_VERSION}/buf-$(uname -s)-$(uname -m)" \
  -o ~/.local/bin/buf
chmod +x ~/.local/bin/buf
```

**Verify Installation**:
```bash
buf --version
# Output: 1.40.1
```

**Add to PATH** (if not already):
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

**Usage**:
```bash
# Lint proto files
cd specs/fleet
buf lint

# Check for breaking changes
buf breaking --against '.git#branch=main'

# Generate code
buf generate

# Update dependencies
buf mod update
```

---

### 2. Podman - Container Engine

**Already Installed** ✅

**Verify**:
```bash
podman --version
# Should show version 4.x or higher
```

**Usage in this project**:
```bash
# Build images
podman build -t myimage:v1.0.0 -f Dockerfile .

# Push to registry
podman push registry.underpassai.com/swe-ai-fleet/myimage:v1.0.0

# Run container
podman run -p 8080:8080 myimage:v1.0.0
```

---

### 3. Python 3.13 (Main) / 3.12 (Ray)

**Already Installed** ✅

**Verify**:
```bash
python --version
# Output: Python 3.13.x

# Virtual environment
source .venv/bin/activate
python --version
```

**Usage**:
```bash
# Always activate venv before running Python commands
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -m 'not e2e and not integration'

# Generate gRPC stubs (when needed locally)
python -m grpc_tools.protoc \
  --proto_path=specs/fleet \
  --python_out=gen/python \
  --grpc_python_out=gen/python \
  orchestrator/v1/orchestrator.proto
```

---

### 4. kubectl - Kubernetes CLI

**Already Installed** ✅

**Verify**:
```bash
kubectl version --client
kubectl get nodes
```

**Common Commands**:
```bash
# Deploy to K8s
kubectl apply -f deploy/k8s/

# Check pods
kubectl get pods -n swe-ai-fleet

# View logs
kubectl logs -n swe-ai-fleet deployment/orchestrator --tail=50

# Delete resources
kubectl delete -f deploy/k8s/11a-orchestrator-delete-councils.yaml
```

---

### 5. grpcurl - gRPC CLI Tool (Optional but Recommended)

**Installation**:
```bash
# Via go install (if Go is installed)
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# Or download binary
curl -sSL https://github.com/fullstorydev/grpcurl/releases/download/v1.9.1/grpcurl_1.9.1_linux_x86_64.tar.gz | tar -xz -C ~/.local/bin
```

**Usage**:
```bash
# List services
grpcurl -plaintext localhost:50055 list

# Describe service
grpcurl -plaintext localhost:50055 describe fleet.orchestrator.v1.OrchestratorService

# Call method
grpcurl -plaintext -d '{"role":"DEV"}' localhost:50055 fleet.orchestrator.v1.OrchestratorService/ListCouncils
```

---

### 6. grpcui - Interactive gRPC Web UI (Optional but Recommended)

**What is grpcui?**
- Web-based UI for testing gRPC endpoints (like Swagger UI for REST)
- Browse services, methods, and schemas
- Execute calls with JSON forms
- View requests/responses in real-time
- Test streaming RPCs

**Installation**:
```bash
# Via install script (recommended)
bash scripts/install-grpcui.sh

# Via go install (if Go is installed)
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
```

**Usage**:
```bash
# From specs/ directory - Launch web UI
make grpcui-serve

# Test specific service
make grpcui-serve SERVICE=orchestrator

# Custom host and port
make grpcui-serve HOST=localhost PORT=50055 SERVICE=orchestrator

# Or manually
grpcui -plaintext localhost:50055
```

**Access**: Open `http://localhost:8080` in your browser

---

## 📋 Tool Versions (Tested)

| Tool | Minimum Version | Recommended | Notes |
|------|----------------|-------------|-------|
| Buf | 1.28.0 | 1.40.1 | For proto validation |
| Podman | 4.0.0 | 5.0+ | Container runtime |
| Python | 3.12.0 | 3.13.0 | Main services |
| Python (Ray) | 3.12.0 | 3.12.12 | Ray cluster |
| kubectl | 1.28.0 | 1.31+ | K8s management |
| grpcurl | 1.8.0 | 1.9.1 | Optional, for testing |
| grpcui | 1.3.0 | 1.3.4 | Optional, for interactive testing |

---

## 🔧 Configuration Files

### Buf Configuration

**Location**: `specs/buf.yaml`

```yaml
version: v2
modules:
  - path: fleet
lint:
  use:
    - STANDARD
    - PACKAGE_VERSION_SUFFIX
breaking:
  use:
    - FILE
```

**Location**: `specs/buf.gen.yaml`

```yaml
version: v2
managed:
  enabled: true
plugins:
  - local: python -m grpc_tools.protoc
    out: ../gen/python
    opt:
      - paths=source_relative
  - local: python -m grpc_tools.protoc --pyi_out
    out: ../gen/python
    opt:
      - paths=source_relative
```

---

## 🐛 Troubleshooting

### Buf not found in PATH

```bash
# Check installation
ls -la ~/.local/bin/buf

# Add to PATH permanently
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or create symlink
sudo ln -s ~/.local/bin/buf /usr/local/bin/buf
```

### Buf version mismatch

```bash
# Uninstall old version
rm ~/.local/bin/buf

# Reinstall latest
./scripts/install-buf.sh
```

### Protocol compiler not found

```bash
# Install grpcio-tools
source .venv/bin/activate
pip install grpcio-tools>=1.60.0
```

### Permission denied when running scripts

```bash
# Make script executable
chmod +x scripts/*.sh

# Run with explicit bash
bash scripts/install-buf.sh
```

---

## 📚 Related Documentation

- [API Versioning Strategy](./API_VERSIONING_STRATEGY.md)
- [API Versioning Implementation](../API_VERSIONING_IMPLEMENTATION.md)
- [Microservices Build Patterns](./MICROSERVICES_BUILD_PATTERNS.md)
- [Buf Official Documentation](https://buf.build/docs/)

---

## ✅ Setup Checklist

Before starting development:

- [ ] Buf installed and in PATH (`buf --version`)
- [ ] Python 3.13 venv activated (`python --version`)
- [ ] Podman working (`podman ps`)
- [ ] kubectl configured (`kubectl get nodes`)
- [ ] Can build Docker images (`podman build --help`)
- [ ] Can access K8s cluster (`kubectl get pods -n swe-ai-fleet`)
- [ ] grpcurl installed (optional but helpful)
- [ ] grpcui installed (optional but helpful for interactive testing)

---

## 🆘 Support

If you encounter issues:

1. Check this troubleshooting section
2. Review tool-specific documentation
3. Check project issues on GitHub
4. Contact project maintainers

---

Last Updated: 2025-10-18

