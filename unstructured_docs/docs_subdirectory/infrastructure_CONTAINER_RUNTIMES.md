# Container Runtimes Guide

This project uses **Kubernetes-native container runtimes** and **OCI-compliant tools** instead of Docker.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Local Development                  Production (Kubernetes)  │
├─────────────────────────────────────────────────────────────┤
│  • Podman (rootless)                • CRI-O                  │
│  • buildah (for builds)             • containerd             │
│  • nerdctl (containerd CLI)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Why Not Docker?

❌ **Requires root daemon**  
❌ **Monolithic design**  
❌ **Not Kubernetes-native**  
❌ **Security concerns**  

✅ **Use Kubernetes-native runtimes instead:**
- **CRI-O** - Purpose-built for Kubernetes
- **containerd** - Industry standard, used by most cloud providers
- **Podman** - Rootless, daemonless, OCI-compliant

## Container Runtimes

### CRI-O (Recommended for Kubernetes)

**What**: Lightweight Container Runtime Interface for Kubernetes  
**Use case**: Production Kubernetes clusters  
**CLI**: `crictl` (low-level), use `podman` or `buildah` for builds  

**Installation** (Arch Linux):
```bash
sudo pacman -S cri-o cri-tools
sudo systemctl enable --now crio
```

**Your project already has CRI-O setup!**
- See: `docs/INSTALL_K8S_CRIO_GPU.md`
- See: `docs/INSTALL_CRIO.md`
- See: `deploy/crio/*.json`

**Check runtime**:
```bash
crictl --runtime-endpoint unix:///var/run/crio/crio.sock version
crictl ps
crictl images
```

### containerd

**What**: Industry-standard container runtime  
**Use case**: Production K8s (AWS EKS, Azure AKS, GKE)  
**CLI**: `ctr` (low-level) or `nerdctl` (Docker-compatible)  

**Installation** (Arch Linux):
```bash
sudo pacman -S containerd nerdctl
sudo systemctl enable --now containerd
```

**Usage**:
```bash
# List containers
nerdctl ps

# Build image
nerdctl build -t myimage .

# Run container
nerdctl run -d myimage

# Docker-compatible!
alias docker=nerdctl
```

## Build Tools

### Podman (Recommended for Local Dev)

**What**: Daemonless, rootless container tool  
**Use case**: Local development, CI/CD, testing  
**Compatible with**: CRI-O, containerd, any OCI runtime  

**Installation** (Arch Linux):
```bash
sudo pacman -S podman podman-compose
```

**Why Podman?**
✅ Rootless (run without sudo)  
✅ Daemonless (no background process)  
✅ Pod support (like Kubernetes)  
✅ Drop-in replacement for Docker CLI  
✅ Generates systemd units  
✅ Works with CRI-O/containerd images  

**Usage**:
```bash
# Build image
podman build -t myimage .

# Run rootless
podman run -d -p 8080:80 myimage

# Create pod (like K8s)
podman pod create --name mypod -p 8080:80
podman run -d --pod mypod myimage

# Generate systemd unit
podman generate systemd --new --files --name mycontainer
systemctl --user enable container-mycontainer.service
```

### buildah

**What**: Specialized tool for building OCI images  
**Use case**: CI/CD pipelines, scripted builds  
**Compatible with**: CRI-O, containerd, any OCI registry  

**Installation** (Arch Linux):
```bash
sudo pacman -S buildah
```

**Why buildah?**
✅ Build without daemon  
✅ Scripted image creation  
✅ No Dockerfile required (but supports it)  
✅ Fine-grained layer control  
✅ Works with CRI-O directly  

**Usage**:
```bash
# Build from Dockerfile
buildah bud -t myimage .

# Scripted build (no Dockerfile)
container=$(buildah from alpine)
buildah run $container apk add --no-cache git
buildah config --cmd "/bin/sh" $container
buildah commit $container myimage

# Push to registry
buildah push myimage ghcr.io/org/myimage:latest
```

### nerdctl

**What**: Docker-compatible CLI for containerd  
**Use case**: Transitioning from Docker, containerd clusters  
**Compatible with**: containerd only  

**Installation** (Arch Linux):
```bash
sudo pacman -S nerdctl
```

**Usage**:
```bash
# Same as Docker!
nerdctl build -t myimage .
nerdctl run -d myimage
nerdctl ps
nerdctl compose up -d
```

## Tool Selection Matrix

| Scenario | Recommended Tool | Why |
|----------|------------------|-----|
| Local dev (rootless) | **Podman** | Rootless, daemonless, full-featured |
| CI/CD builds | **buildah** | Scriptable, no daemon, fast |
| containerd users | **nerdctl** | Docker-compatible, native |
| K8s production | **CRI-O** or **containerd** | Purpose-built for K8s |
| Multi-container local | **podman-compose** | Rootless compose |

## This Project's Makefile

The Makefile auto-detects your tools in priority order:

1. **Podman** - Full-featured, rootless
2. **buildah** - Build-only, scriptable
3. **nerdctl** - containerd CLI

```bash
# Auto-detect (uses first available)
make docker-build

# Force specific tool
CONTAINER_ENGINE=podman make docker-build
CONTAINER_ENGINE=buildah make docker-build
CONTAINER_ENGINE=nerdctl make docker-build
```

## Installation Guide

### Arch Linux (Your System)

**Option 1: Podman (Recommended)**
```bash
# Install Podman
sudo pacman -S podman podman-compose podman-docker

# Setup rootless
sudo sysctl kernel.unprivileged_userns_clone=1
echo 'kernel.unprivileged_userns_clone=1' | sudo tee /etc/sysctl.d/99-podman.conf

# Configure subuid/subgid
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(whoami)

# Test
podman info
podman run -d -p 8080:80 nginx:alpine
```

**Option 2: CRI-O + buildah**
```bash
# Install CRI-O and buildah
sudo pacman -S cri-o buildah cri-tools

# Enable CRI-O
sudo systemctl enable --now crio

# Test
buildah version
crictl version
```

**Option 3: containerd + nerdctl**
```bash
# Install containerd and nerdctl
sudo pacman -S containerd nerdctl

# Enable containerd
sudo systemctl enable --now containerd

# Test
nerdctl version
nerdctl run -d nginx:alpine
```

## Kubernetes Integration

### Using CRI-O

Your cluster is already configured! (See `docs/INSTALL_K8S_CRIO_GPU.md`)

```bash
# Check runtime
kubectl get nodes -o wide | grep CONTAINER-RUNTIME

# Verify CRI-O
crictl --runtime-endpoint unix:///var/run/crio/crio.sock info

# Deploy
kubectl apply -f deploy/k8s-new/
```

### Using containerd

```bash
# Check runtime
kubectl get nodes -o wide

# Should show: containerd://1.7.x

# Deploy (same manifests work)
kubectl apply -f deploy/k8s-new/
```

## Image Compatibility

All tools produce **OCI-compliant images** that work everywhere:

```bash
# Build with Podman
podman build -t myimage .

# Push to registry
podman push myimage ghcr.io/org/myimage:latest

# Pull and run with CRI-O (in K8s)
kubectl run myapp --image=ghcr.io/org/myimage:latest

# Or with containerd/nerdctl
nerdctl pull ghcr.io/org/myimage:latest
nerdctl run -d ghcr.io/org/myimage:latest
```

## Security Benefits

### Rootless Podman
```bash
# No sudo required!
podman run -d -p 8080:80 nginx

# Check user
podman unshare cat /proc/self/uid_map
# Shows user namespace mapping
```

### CRI-O Security
- **Runs as systemd service** (not root daemon)
- **SELinux integration** (on RHEL/Fedora)
- **Seccomp profiles** by default
- **No privileged daemon**

## Migration Path

### From Docker

```bash
# 1. Install Podman
sudo pacman -S podman

# 2. Alias (optional)
alias docker=podman
alias docker-compose=podman-compose

# 3. Use existing commands
podman build -t myimage .
podman run -d myimage
podman ps
```

Most Docker commands work unchanged with Podman!

## Performance Comparison

All runtimes use the same low-level tools (runc/crun):

| Runtime | Build Time | Run Performance | Startup Time |
|---------|------------|-----------------|--------------|
| Podman | Similar | Same | Same |
| buildah | Slightly faster | N/A (build only) | N/A |
| CRI-O | N/A | Same | Slightly faster |
| containerd | N/A | Same | Same |

**Verdict**: Negligible difference in performance. Choose based on features and use case.

## Resources

- [CRI-O Documentation](https://cri-o.io/)
- [containerd Documentation](https://containerd.io/)
- [Podman Documentation](https://docs.podman.io/)
- [buildah Documentation](https://buildah.io/)
- [nerdctl Documentation](https://github.com/containerd/nerdctl)
- [OCI Specification](https://opencontainers.org/)

## Your Project's Existing Docs

This project already documents CRI-O extensively:
- `docs/INSTALL_K8S_CRIO_GPU.md` - Full K8s + CRI-O + GPU setup
- `docs/INSTALL_CRIO.md` - CRI-O installation
- `docs/TROUBLESHOOTING_CRIO.md` - CRI-O troubleshooting
- `docs/CRIO_DIAGNOSTICS.md` - Diagnostic tools
- `deploy/crio/*.json` - CRI-O manifests

## Summary

**Local Development**: Use **Podman** (rootless, full-featured)  
**CI/CD Builds**: Use **buildah** (scriptable, fast)  
**Production K8s**: Use **CRI-O** (K8s-native) or **containerd** (industry standard)  

**No Docker needed!** All tools are OCI-compliant and work together seamlessly.



