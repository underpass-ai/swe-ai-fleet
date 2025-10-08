# Infrastructure Deployment Scripts

Scripts for deploying SWE AI Fleet to Kubernetes.

## 🚀 Quick Start

```bash
# 1. Verify prerequisites
./00-verify-prerequisites.sh

# 2. Deploy everything
./deploy-all.sh

# 3. Verify health
./verify-health.sh
```

## 📋 Scripts

### Deployment Scripts (Run in Order)

| Script | Description |
|--------|-------------|
| `00-verify-prerequisites.sh` | Check cluster readiness |
| `01-deploy-namespace.sh` | Create namespace |
| `02-deploy-nats.sh` | Deploy NATS JetStream |
| `03-deploy-config.sh` | Deploy ConfigMaps |
| `04-deploy-services.sh` | Deploy all microservices |
| `05-deploy-ui.sh` | (Optional) Expose UI publicly |
| `06-expose-ui.sh` | Configure UI ingress with DNS |
| `07-expose-ray-dashboard.sh` | Configure Ray Dashboard ingress |

### Utility Scripts

| Script | Description |
|--------|-------------|
| `deploy-all.sh` | Run all deployment steps automatically |
| `verify-health.sh` | Check system health |

## 📝 Usage

### Full Deployment

```bash
./deploy-all.sh
```

This will:
1. Create namespace
2. Deploy NATS
3. Deploy ConfigMaps
4. Deploy microservices
5. Verify health

### Step-by-Step Deployment

```bash
# Check prerequisites first
./00-verify-prerequisites.sh

# Deploy core components
./01-deploy-namespace.sh
./02-deploy-nats.sh
./03-deploy-config.sh
./04-deploy-services.sh

# Verify
./verify-health.sh

# Optional: Expose UI
./06-expose-ui.sh
```

### Customization

#### Change Domain

Before running `06-expose-ui.sh`, edit the domain in `../../deploy/k8s/05-ui-ingress.yaml`:

```yaml
- host: your-domain.com  # Change this
```

#### Adjust Resources

Edit `../../deploy/k8s/04-services.yaml` to modify:
- CPU/memory requests/limits
- Number of replicas
- Image versions

## 🔍 Verification

### Check Pod Status

```bash
./verify-health.sh
```

### Manual Checks

```bash
# Pods
kubectl get pods -n swe-ai-fleet

# Services
kubectl get svc -n swe-ai-fleet

# Ingress
kubectl get ingress -n swe-ai-fleet

# Logs
kubectl logs -n swe-ai-fleet -l app=planning --tail=50
```

## 🔄 Rollback

### Remove Everything

```bash
kubectl delete namespace swe-ai-fleet
```

### Remove Specific Component

```bash
# Remove UI ingress
kubectl delete ingress po-ui-ingress -n swe-ai-fleet

# Remove a service
kubectl delete deployment planning -n swe-ai-fleet
```

## ⚠️ Prerequisites

Before running these scripts, ensure:

1. **Kubernetes Cluster**
   - Version 1.28+
   - GPU support (optional, for RayCluster)

2. **Installed Components**
   - cert-manager (for TLS)
   - ingress-nginx (for external access)
   - KubeRay Operator (optional, for agent execution)

3. **Configuration**
   - kubectl configured
   - DNS records created
   - Container images pushed to registry

4. **Environment**
   - bash shell
   - kubectl CLI
   - aws CLI (for Route53 DNS)

## 🐛 Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod <pod-name> -n swe-ai-fleet
kubectl logs <pod-name> -n swe-ai-fleet
```

### Image Pull Errors

Check image names in `../../deploy/k8s/04-services.yaml` and ensure they're accessible.

### Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n swe-ai-fleet

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

### DNS Not Resolving

Verify Route53 record points to ingress LoadBalancer IP:

```bash
# Get LoadBalancer IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Check DNS
nslookup swe-fleet.your-domain.com
```

## 📚 Documentation

- [Getting Started](../../docs/getting-started/README.md)
- [Architecture](../../docs/architecture/README.md)
- [Operations](../../docs/operations/README.md)
- [Troubleshooting](../../docs/operations/troubleshooting.md)

## 🤝 Contributing

See [Contributing Guide](../../CONTRIBUTING.md) for how to contribute to these scripts.
