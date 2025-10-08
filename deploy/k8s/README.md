# Kubernetes Manifests - Production Deployment

This directory contains the production-ready Kubernetes manifests for SWE AI Fleet.

## 📋 Files

| File | Description |
|------|-------------|
| `00-namespace.yaml` | Creates `swe-ai-fleet` namespace |
| `01-nats.yaml` | Deploys NATS JetStream (messaging backbone) |
| `02-nats-internal-dns.yaml` | Internal DNS services for all microservices |
| `03-configmaps.yaml` | FSM workflow and rigor profiles configuration |
| `04-services.yaml` | Planning, StoryCoach, Workspace, and PO UI |
| `05-ui-ingress.yaml` | Public HTTPS access to PO UI |
| `06-ray-dashboard-ingress.yaml` | Public HTTPS access to Ray Dashboard |
| `07-registry.yaml` | Local container registry (optional) |

## 🚀 Quick Deployment

Use the deployment scripts for easy setup:

```bash
# From project root
cd scripts/infra
./deploy-all.sh
```

## 📝 Manual Deployment

If you prefer step-by-step deployment:

```bash
# 1. Create namespace
kubectl apply -f 00-namespace.yaml

# 2. Deploy NATS
kubectl apply -f 01-nats.yaml
kubectl apply -f 02-nats-internal-dns.yaml

# 3. Deploy configuration
kubectl apply -f 03-configmaps.yaml

# 4. Deploy microservices
kubectl apply -f 04-services.yaml

# 5. (Optional) Expose UI publicly
kubectl apply -f 05-ui-ingress.yaml

# 6. (Optional) Expose Ray Dashboard
kubectl apply -f 06-ray-dashboard-ingress.yaml
```

## 🔧 Prerequisites

Before deploying, ensure you have:

- Kubernetes cluster (1.28+)
- kubectl configured
- cert-manager installed (for TLS certificates)
- ingress-nginx installed (for external access)
- Container images pushed to your registry

See `docs/getting-started/prerequisites.md` for detailed requirements.

## 📊 Verify Deployment

```bash
# Check pod status
kubectl get pods -n swe-ai-fleet

# Check services
kubectl get svc -n swe-ai-fleet

# Check ingress
kubectl get ingress -n swe-ai-fleet
```

## 🔄 Rollback

To completely remove the deployment:

```bash
kubectl delete namespace swe-ai-fleet
```

## 📚 Documentation

- [Getting Started Guide](../../docs/getting-started/README.md)
- [Architecture Overview](../../docs/architecture/README.md)
- [Troubleshooting](../../docs/operations/troubleshooting.md)

## 🎯 Customization

### Change Domain Names

Edit the ingress files (`05-ui-ingress.yaml`, `06-ray-dashboard-ingress.yaml`) and replace:
- `swe-fleet.underpassai.com` → your domain
- `ray.underpassai.com` → your domain

### Adjust Resources

Edit `04-services.yaml` to modify CPU/memory limits for each service.

### Enable/Disable Components

Comment out sections in `02-nats-internal-dns.yaml` to disable internal DNS services.

## ⚠️ Important Notes

- **Images**: Update image references in `04-services.yaml` to point to your registry
- **TLS**: Requires cert-manager with a valid ClusterIssuer
- **DNS**: Requires DNS records pointing to your ingress LoadBalancer IP
- **GPU**: RayCluster (optional) requires GPU-enabled nodes
