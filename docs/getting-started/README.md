# Getting Started with SWE AI Fleet

Welcome to SWE AI Fleet! This guide will help you deploy the system to your Kubernetes cluster.

## 🎯 What is SWE AI Fleet?

SWE AI Fleet is an **AI-powered software engineering platform** that orchestrates teams of AI agents to collaboratively solve complex coding tasks. It features:

- **Multi-agent deliberation** with peer review
- **FSM-driven workflows** for managing user stories
- **GPU-accelerated execution** with Ray
- **Context-aware agents** powered by knowledge graphs
- **Microservices architecture** with gRPC and NATS

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured
- 512GB RAM, 4x RTX 3090 recommended (see [prerequisites.md](prerequisites.md))

### Deploy

```bash
# Clone the repository
git clone https://github.com/yourusername/swe-ai-fleet
cd swe-ai-fleet

# Verify prerequisites
./scripts/infra/00-verify-prerequisites.sh

# Deploy everything
./scripts/infra/deploy-all.sh
```

### Access

- **UI:** Configure domain in `deploy/k8s/05-ui-ingress.yaml`, then run `./scripts/infra/06-expose-ui.sh`
- **Ray Dashboard:** Run `./scripts/infra/07-expose-ray-dashboard.sh`
- **Internal Services:** Available via DNS (internal.nats.underpassai.com, etc.)

## 📚 Detailed Guides

### 1. [Prerequisites](prerequisites.md)
Hardware, software, and cluster requirements.

### 2. [Installation](installation.md)
Step-by-step installation guide.

### 3. [Quickstart](quickstart.md)
Deploy in 5 minutes.

## 🏗️ Architecture Overview

SWE AI Fleet consists of:

- **NATS JetStream**: Asynchronous messaging backbone
- **Planning Service**: FSM-based workflow management
- **StoryCoach Service**: User story quality scoring
- **Workspace Service**: Agent work validation
- **PO UI**: React-based Product Owner interface
- **RayCluster**: GPU-accelerated agent execution (optional)

See [Architecture Documentation](../architecture/README.md) for details.

## 🔍 What's Next?

After deployment:

1. **Explore the UI**: https://swe-fleet.yourdomain.com
2. **Monitor agents**: https://ray.yourdomain.com
3. **Read the docs**: [Architecture](../architecture/README.md), [Operations](../operations/README.md)
4. **Contribute**: [Development Guide](../development/README.md)

## 🆘 Need Help?

- **Troubleshooting**: [Operations Guide](../operations/troubleshooting.md)
- **FAQ**: [Reference](../reference/faq.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/swe-ai-fleet/issues)
- **Community**: [Discord](https://discord.gg/yourserver)

## 📝 Configuration

### Change Domains

Edit ingress files in `deploy/k8s/`:
- `05-ui-ingress.yaml`: Change `swe-fleet.underpassai.com`
- `06-ray-dashboard-ingress.yaml`: Change `ray.underpassai.com`

### Adjust Resources

Edit `deploy/k8s/04-services.yaml` to modify CPU/memory limits.

### Enable/Disable Components

Comment out sections in manifests to disable optional components.

## 🎓 Learning Resources

- [Vision & Roadmap](../vision/VISION.md)
- [Use Cases](../vision/USE_CASES.md)
- [RFCs](../reference/rfcs/)
- [Architecture Decision Records](../reference/adrs/)

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](../development/CONTRIBUTING.md).

## 📄 License

This project is licensed under the [Apache 2.0 License](../../LICENSE).
