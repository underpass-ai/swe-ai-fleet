# Podman & CRI-O Guide for SWE AI Fleet

Guide for running SWE AI Fleet with **Podman** (rootless containers) and **CRI-O** (Kubernetes native runtime).

## Why Podman or CRI-O?

### Podman Benefits
✅ **Rootless** - Run containers without root privileges  
✅ **Daemonless** - No background daemon required  
✅ **Drop-in Docker replacement** - Compatible CLI  
✅ **Pod support** - Native Kubernetes pod concept  
✅ **systemd integration** - Generate systemd units  
✅ **Security** - Better isolation, SELinux support  

### CRI-O Benefits
✅ **Kubernetes native** - Built for K8s only  
✅ **Lightweight** - No extra features, just CRI  
✅ **OCI compliant** - Works with any OCI runtime  
✅ **Performance** - Optimized for container orchestration  

## Installation

### Podman

#### Arch Linux (your system)
```bash
sudo pacman -S podman podman-compose podman-docker
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y podman podman-compose
```

#### RHEL/Fedora
```bash
sudo dnf install -y podman podman-compose
```

#### Verify
```bash
podman --version
podman-compose --version
```

### CRI-O

#### For Kubernetes nodes
```bash
# See existing guide
cat docs/INSTALL_K8S_CRIO_GPU.md
```

CRI-O is already documented in your project for K8s GPU nodes.

## Using Podman (Rootless)

### Setup Rootless Podman

```bash
# Enable user namespaces
sudo sysctl kernel.unprivileged_userns_clone=1
echo 'kernel.unprivileged_userns_clone=1' | sudo tee /etc/sysctl.d/99-podman.conf

# Configure subuid/subgid (if not already set)
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(whoami)

# Verify
podman info
```

### Building Images with Podman

The Makefile auto-detects Podman:

```bash
cd services

# Build all images (uses Podman if available)
make docker-build

# Force Podman
CONTAINER_ENGINE=podman make docker-build

# Build specific service
make docker-build-planning

# Build with custom registry
REGISTRY=my-registry.com/my-org VERSION=v1.0.0 make docker-build
```

### Running with Podman Compose

```bash
# Start all services (rootless)
podman-compose -f podman-compose.yml up -d

# View logs
podman-compose logs -f planning

# Check status
podman-compose ps

# Stop all services
podman-compose down

# Clean volumes
podman volume prune
```

### Running with Podman Pods

Podman has native pod support (like Kubernetes):

```bash
# Create a pod
podman pod create --name swe-fleet \
  -p 4222:4222 \
  -p 8222:8222 \
  -p 50051:50051 \
  -p 50052:50052 \
  -p 50053:50053 \
  -p 3000:80

# Run containers in the pod
podman run -d --pod swe-fleet \
  --name nats \
  nats:2.10-alpine --jetstream

podman run -d --pod swe-fleet \
  --name planning \
  -v $PWD/config:/app/config:ro,z \
  ghcr.io/underpass-ai/swe-fleet/planning:latest

podman run -d --pod swe-fleet \
  --name storycoach \
  ghcr.io/underpass-ai/swe-fleet/storycoach:latest

# Check pod
podman pod ps
podman pod logs swe-fleet

# Stop pod
podman pod stop swe-fleet

# Remove pod
podman pod rm swe-fleet
```

### Generate Systemd Units (Auto-start on boot)

```bash
# Start services with podman-compose
podman-compose up -d

# Generate systemd units
cd ~/.config/systemd/user
podman generate systemd --new --files --name swe-planning
podman generate systemd --new --files --name swe-nats

# Enable services
systemctl --user enable container-swe-planning.service
systemctl --user enable container-swe-nats.service
systemctl --user daemon-reload

# Start services
systemctl --user start container-swe-planning.service

# Check status
systemctl --user status container-swe-planning.service
```

### Rootless Port Binding

Rootless Podman can't bind to ports < 1024 by default. Solutions:

**Option 1: Use port forwarding (recommended)**
```bash
# Bind to unprivileged port
podman run -p 8080:80 ...

# Forward with iptables (requires root once)
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
```

**Option 2: Lower limit (system-wide)**
```bash
sudo sysctl net.ipv4.ip_unprivileged_port_start=80
```

**Option 3: Use slirp4netns with port handler**
```bash
podman run --network slirp4netns:port_handler=slirp4netns -p 80:80 ...
```

## Using CRI-O with Kubernetes

Your project already has CRI-O configured! See:
- `docs/INSTALL_K8S_CRIO_GPU.md` - Full K8s + CRI-O + GPU setup
- `docs/INSTALL_CRIO.md` - CRI-O installation guide
- `deploy/crio/*.json` - Podman/CRI-O manifests for services

### Deploy to CRI-O/K8s

```bash
# Your existing K8s deployment uses CRI-O
kubectl apply -f deploy/k8s-new/

# Verify CRI-O is used
kubectl get nodes -o wide
# Look for CONTAINER-RUNTIME: cri-o://...

# Check container runtime
crictl --runtime-endpoint unix:///var/run/crio/crio.sock ps
```

## Podman vs Docker Feature Comparison

| Feature | Docker | Podman | CRI-O |
|---------|--------|--------|-------|
| Rootless | Partial | Full | N/A |
| Daemon | Required | No | systemd |
| Kubernetes | Via K8s | Via K8s | Native |
| Pod support | No | Yes | Yes |
| Systemd integration | No | Yes | Yes |
| Docker CLI compatible | Yes | Yes | No |
| BuildKit | Yes | Yes | Yes |
| Multi-arch | Yes | Yes | Yes |

## SELinux Considerations

Podman works great with SELinux (Arch Linux doesn't use it by default, but good to know):

```bash
# Label volumes correctly
podman run -v /path/to/config:/app/config:ro,z ...

# :z - Private label (single container)
# :Z - Shared label (multiple containers)

# Check labels
ls -Z /path/to/config
```

## Performance Comparison

### Build Performance
```bash
# Benchmark: Build Planning service

# Docker
time docker build -f services/planning/Dockerfile .
# Real: ~45s

# Podman
time podman build -f services/planning/Dockerfile .
# Real: ~42s (similar, sometimes faster)

# With BuildKit cache
time podman build --cache-from=... -f services/planning/Dockerfile .
# Real: ~8s
```

### Runtime Performance
Negligible difference - both use runc/crun as low-level runtime.

## Troubleshooting

### "permission denied" errors

Check user namespaces:
```bash
cat /proc/sys/kernel/unprivileged_userns_clone
# Should be 1

# If 0, enable:
sudo sysctl kernel.unprivileged_userns_clone=1
```

### "no such file or directory" for subuid/subgid

Setup subordinate UIDs/GIDs:
```bash
sudo usermod --add-subuids 100000-165535 $(whoami)
sudo usermod --add-subgids 100000-165535 $(whoami)
podman system migrate
```

### Slow DNS resolution

Configure DNS:
```bash
cat ~/.config/containers/containers.conf
[network]
dns_servers = ["8.8.8.8", "1.1.1.1"]
```

### Volume mount permission issues

Use `:z` or `:Z` label:
```bash
podman run -v $PWD/config:/app/config:ro,z ...
```

### "ERRO[0000] cannot find UID/GID"

Reset storage:
```bash
podman system reset
```

### CRI-O Issues

Your project already documents these:
```bash
# See existing troubleshooting
cat docs/TROUBLESHOOTING_CRIO.md
```

## Hybrid Deployment

You can mix Docker and Podman:

```bash
# Build with Docker
CONTAINER_ENGINE=docker make docker-build-planning

# Run with Podman
podman run -d -p 50051:50051 \
  ghcr.io/underpass-ai/swe-fleet/planning:latest

# Or vice versa
CONTAINER_ENGINE=podman make docker-build-storycoach
docker run -d -p 50052:50052 \
  ghcr.io/underpass-ai/swe-fleet/storycoach:latest
```

Images are OCI-compliant and work with any runtime.

## Migration from Docker

### Replace Docker Desktop

```bash
# Install Podman
sudo pacman -S podman podman-compose podman-docker

# Alias docker to podman (optional)
alias docker=podman
alias docker-compose=podman-compose

# Or use podman-docker package (provides /usr/bin/docker)
```

### Update Existing Scripts

Most scripts work unchanged:
```bash
# These work with podman via alias
docker build -t myimage .
docker run -d myimage
docker ps
docker logs <container>
```

### Move Docker Volumes to Podman

```bash
# Export from Docker
docker run --rm -v myvolume:/data -v $(pwd):/backup \
  alpine tar czf /backup/myvolume.tar.gz /data

# Import to Podman
podman volume create myvolume
podman run --rm -v myvolume:/data -v $(pwd):/backup \
  alpine tar xzf /backup/myvolume.tar.gz -C /
```

## Best Practices

### For Local Development
✅ Use **Podman** rootless for security  
✅ Use `podman-compose` for multi-container apps  
✅ Generate systemd units for services  
✅ Label volumes with `:z` or `:Z`  

### For CI/CD
✅ Use **Podman** in GitLab CI (native support)  
✅ Use **Docker** in GitHub Actions (better support)  
✅ Test images with both runtimes  

### For Production (K8s)
✅ Use **CRI-O** as container runtime  
✅ Follow existing guides in `/docs/`  
✅ GPU nodes already configured  

## Resources

- [Podman Documentation](https://docs.podman.io/)
- [Podman vs Docker](https://developers.redhat.com/articles/podman-next-generation-linux-container-tools)
- [CRI-O Documentation](https://cri-o.io/)
- [Your CRI-O Setup](docs/INSTALL_K8S_CRIO_GPU.md)
- [Rootless Containers](https://rootlesscontaine.rs/)

## Quick Commands

```bash
# Podman
podman version
podman info
podman build -t image:tag .
podman run -d image:tag
podman ps
podman logs <container>
podman stop <container>
podman system prune

# Podman Compose
podman-compose up -d
podman-compose ps
podman-compose logs -f
podman-compose down

# CRI-O (via crictl)
crictl --runtime-endpoint unix:///var/run/crio/crio.sock ps
crictl images
crictl logs <container-id>

# Makefile (auto-detects)
make docker-build              # Uses Podman if available
CONTAINER_ENGINE=podman make docker-build
CONTAINER_ENGINE=docker make docker-build
```

## Next Steps

1. **Try Podman locally**: Build and run services rootless
2. **Generate systemd units**: Auto-start services on boot
3. **Deploy to K8s with CRI-O**: Use existing deployment guides
4. **Monitor performance**: Compare Podman vs Docker in your workflow



