# SWE AI Fleet Documentation

Welcome to the SWE AI Fleet documentation! This project is an open-source, multi-agent system for software development and systems architecture.

## 📚 Documentation Index

### 🚀 Getting Started
- [Quick Start Guide](quickstart.md) - Get up and running with SWE AI Fleet
- [Installation Guide](installation.md) - Detailed installation instructions
- [Configuration Guide](configuration.md) - Configure your SWE AI Fleet deployment

### 🏗️ Architecture & Design
- [System Architecture](architecture.md) - High-level system design and components
- [Agent System](agents.md) - Understanding the multi-agent architecture
- [Memory System](memory.md) - Long-term knowledge graph and short-term memory
- [Tool System](tools.md) - Safe tool wrappers and integrations

### 🔧 Development & Operations
- [Development Guide](development.md) - Contributing to SWE AI Fleet
- [Deployment Guide](deployment.md) - Deploying to various environments
- [API Reference](api.md) - Complete API documentation
- [CLI Reference](cli.md) - Command-line interface documentation

### 📋 Standards & Processes
- [Architecture Decision Records (ADRs)](adr/) - Design decisions and rationale
- [Request for Comments (RFCs)](rfc/) - Proposed changes and specifications
- [Contributing Guidelines](../CONTRIBUTING.md) - How to contribute to the project
- [Code of Conduct](../CODE_OF_CONDUCT.md) - Community standards

### 🧪 Testing & Quality
- [Testing Guide](testing.md) - Running tests and quality assurance
- [Performance Guide](performance.md) - Performance optimization and monitoring

## 🎯 What is SWE AI Fleet?

SWE AI Fleet is a sophisticated multi-agent system that orchestrates role-based LLM agents for software development tasks. It provides:

- **Multi-Agent Orchestration**: Role-based agents (developers, devops, data, QA, architect)
- **Distributed Computing**: Built on Ray/KubeRay for scalable execution
- **Safe Tool Integration**: Wrappers for kubectl, helm, psql, and other tools
- **Knowledge Management**: Long-term knowledge graph (Neo4j) + short-term memory (Redis)
- **Local-First Approach**: Designed for edge computing and local development

## 🏁 Quick Start

For immediate setup, see our [Quick Start Guide](quickstart.md). The basic requirements are:

- Python 3.13+
- Docker
- kind (Kubernetes in Docker)
- kubectl
- helm

## 📖 Additional Resources

- [GitHub Repository](https://github.com/tgarciai/swe-ai-fleet)
- [Issue Tracker](https://github.com/tgarciai/swe-ai-fleet/issues)
- [Discussions](https://github.com/tgarciai/swe-ai-fleet/discussions)
- [Releases](https://github.com/tgarciai/swe-ai-fleet/releases)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](../CONTRIBUTING.md) and [Development Guide](development.md) for details on how to get involved.

---

*Last updated: $(date)*