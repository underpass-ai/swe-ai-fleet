# Prerequisites

## 🖥️ Recommended Hardware

### Production Setup

- **CPU**: AMD Threadripper PRO 5955WX (16c/32t) or equivalent
- **RAM**: 512GB DDR4 ECC (8x64GB, 8 channels)
- **GPU**: 4x NVIDIA RTX 3090 (24GB VRAM each) = 96GB total
- **Storage**: 2TB NVMe SSD
- **Network**: 10GbE recommended

### Minimum Setup

- **CPU**: 16 cores / 32 threads
- **RAM**: 128GB
- **GPU**: 1x NVIDIA GPU with 16GB+ VRAM
- **Storage**: 500GB SSD
- **Network**: 1GbE

### Development Setup

- **CPU**: 8 cores
- **RAM**: 32GB
- **GPU**: Optional (for agent execution)
- **Storage**: 100GB

## ☸️ Kubernetes Requirements

### Cluster

- **Version**: 1.28 or later
- **Container Runtime**: CRI-O, containerd, or Docker
- **Nodes**: 1+ (single-node or multi-node)
- **GPU Support**: NVIDIA GPU Operator (for GPU workloads)

### Installed Components

#### Required

- **cert-manager** (v1.13+)
  - For automatic TLS certificate management
  - Requires ClusterIssuer configured (e.g., Let's Encrypt with Route53)

- **ingress-nginx** (v1.9+)
  - For external access to services
  - Requires LoadBalancer (MetalLB or cloud LB)

#### Optional

- **KubeRay Operator** (v1.4+)
  - For distributed agent execution
  - Only needed if using RayCluster

- **NVIDIA GPU Operator** (v25+)
  - For GPU support
  - Enables time-slicing for multi-tenancy

- **MetalLB** (for bare-metal clusters)
  - Provides LoadBalancer service type
  - Not needed on cloud providers

### Storage

- **Default StorageClass** configured
- At least 100GB available for PersistentVolumeClaims

## 🛠️ Software Requirements

### Local Machine

- **kubectl** (v1.28+)
- **bash** (4.0+)
- **git**
- **aws CLI** (if using Route53 for DNS)

### Container Tools (for building images)

One of:
- **podman** + **buildah**
- **nerdctl**
- **docker**

## 🌐 Network Requirements

### DNS

- Domain name (e.g., `underpassai.com`)
- Access to DNS provider (Route53, Cloudflare, etc.)
- Ability to create A records

### Firewall

- Ingress traffic on ports 80, 443 (HTTPS)
- Egress to container registries (docker.io, ghcr.io, etc.)

### Load Balancer

- External IP for ingress-nginx
- Static IP recommended for production

## 🔐 Access Requirements

### Kubernetes

- Cluster admin access (`cluster-admin` role)
- kubeconfig file configured

### Container Registry

One of:
- Local registry (deploy/k8s/07-registry.yaml)
- Docker Hub
- GitHub Container Registry
- AWS ECR
- Google Container Registry

### DNS Provider

- Route53: AWS credentials with Route53 full access
- Cloudflare: API token
- Other: API access for DNS management

## ✅ Verification

Run the prerequisite check script:

```bash
./scripts/infra/00-verify-prerequisites.sh
```

This will verify:
- kubectl is installed and configured
- Cluster is accessible
- Required components are installed
- GPU support (if applicable)

## 📚 Installation Guides

If you need to install prerequisites:

- [Kubernetes with CRI-O and GPU](../infrastructure/kubernetes.md)
- [cert-manager Setup](https://cert-manager.io/docs/installation/)
- [ingress-nginx Setup](https://kubernetes.github.io/ingress-nginx/deploy/)
- [KubeRay Operator](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started.html)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/getting-started.html)

## 🐛 Troubleshooting

See [Troubleshooting Guide](../operations/troubleshooting.md) for common issues.
