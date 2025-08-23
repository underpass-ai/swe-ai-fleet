# Quick Start Guide

This guide will get you up and running with SWE AI Fleet in minutes. SWE AI Fleet is a multi-agent system for software development that orchestrates role-based LLM agents with distributed computing capabilities.

## 🚀 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - [Download Python](https://www.python.org/downloads/)
- **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
- **kind** - [Install kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- **kubectl** - [Install kubectl](https://kubernetes.io/docs/tasks/tools/)
- **helm** - [Install Helm](https://helm.sh/docs/intro/install/)

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/tgarciai/swe-ai-fleet.git
cd swe-ai-fleet
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e .
pip install -r requirements-dev.txt  # For development
```

## 🏃‍♂️ Quick Start

### Option 1: Local Development Stack

The easiest way to get started is using the local development stack:

```bash
# Start the local infrastructure
./scripts/start_local_stack.sh

# Run the end-to-end example
swe_ai_fleet-e2e examples/simple_cluster.yaml
```

### Option 2: Manual Setup

If you prefer to set up components manually:

#### 1. Start Redis

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

#### 2. Start Neo4j

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5
```

#### 3. Start kind Cluster

```bash
kind create cluster --name swe-ai-fleet
kubectl cluster-info --context kind-swe-ai-fleet
```

#### 4. Install KubeRay

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator
```

## 🧪 Verify Installation

### Check Infrastructure Status

```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check Neo4j
curl -u neo4j:password http://localhost:7474/browser/

# Check Kubernetes
kubectl get nodes
kubectl get pods -A
```

### Run a Simple Test

```bash
# Test the CLI
swe_ai_fleet-e2e --help

# Run a basic example
python -m pytest tests/ -v
```

## 📁 Project Structure

```
swe_ai_fleet/
├── src/swe_ai_fleet/
│   ├── agents/          # Role-based AI agents
│   ├── orchestrator/    # Multi-agent orchestration
│   ├── tools/          # Safe tool wrappers
│   ├── memory/         # Knowledge management
│   ├── models/         # Data models
│   └── cli/            # Command-line interface
├── examples/            # Example configurations
├── tests/              # Test suite
├── deploy/             # Deployment manifests
└── scripts/            # Utility scripts
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Ray Configuration
RAY_HEAD_HOST=localhost
RAY_HEAD_PORT=10001
```

### Agent Configuration

Create a YAML configuration file for your agents:

```yaml
# examples/my_cluster.yaml
agents:
  - name: developer
    role: software_developer
    tools: ["git", "python", "docker"]
    
  - name: devops
    role: devops_engineer
    tools: ["kubectl", "helm", "terraform"]
    
  - name: architect
    role: systems_architect
    tools: ["diagrams", "planning"]

memory:
  redis:
    host: localhost
    port: 6379
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: password
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :6379  # For Redis
lsof -i :7474  # For Neo4j

# Kill the process or use different ports
```

#### 2. Python Version Issues
```bash
# Ensure you're using Python 3.13+
python --version

# If you have multiple Python versions
python3.13 -m venv venv
```

#### 3. Docker Permission Issues
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

#### 4. Kubernetes Connection Issues
```bash
# Check kind cluster status
kind get clusters
kind delete cluster --name swe-ai-fleet
kind create cluster --name swe-ai-fleet
```

### Getting Help

- **GitHub Issues**: [Report bugs](https://github.com/tgarciai/swe-ai-fleet/issues)
- **Discussions**: [Ask questions](https://github.com/tgarciai/swe-ai-fleet/discussions)
- **Documentation**: Check other sections of this documentation

## 🎯 Next Steps

Now that you have SWE AI Fleet running, explore:

1. **[Architecture Guide](architecture.md)** - Understand the system design
2. **[Agent System](agents.md)** - Learn about the multi-agent architecture
3. **[Tool System](tools.md)** - Explore available tools and integrations
4. **[Examples](../examples/)** - Try different agent configurations
5. **[Development Guide](development.md)** - Contribute to the project

## 🆘 Need Help?

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#-troubleshooting) above
2. Search existing [GitHub issues](https://github.com/tgarciai/swe-ai-fleet/issues)
3. Start a [discussion](https://github.com/tgarciai/swe-ai-fleet/discussions)
4. Review the [contributing guidelines](../CONTRIBUTING.md)

---

*Happy coding with SWE AI Fleet! 🚀*