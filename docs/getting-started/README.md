# Getting Started

Entry point for deploying and developing SWE AI Fleet.

## Read First

1. `docs/getting-started/prerequisites.md`
2. `deploy/k8s/README.md`
3. `docs/QUICK_START.md`
4. `docs/MODULAR_ARCHITECTURE.md`

## Typical Paths

Production or cluster deployment:

- Follow `deploy/k8s/README.md`
- Use Make targets such as `make deploy-build`, `make deploy-build-no-cache`, and `make deploy`

Local development:

1. Install dependencies: `make install-deps`
2. Generate protobuf stubs: `make generate-protos`
3. Start required infra (Neo4j, Valkey, NATS, Ray) in your environment
4. Start services from `services/*/server.py` as needed
5. Run tests with `make test-unit` or `make test-module MODULE=<path>`

## Useful References

- Architecture overview: `docs/architecture/OVERVIEW.md`
- Service inventory: `docs/architecture/MICROSERVICES.md`
- Core contexts: `docs/architecture/CORE_CONTEXTS.md`
