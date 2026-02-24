# Quick Start

Practical commands for day-to-day development.

## 1) Discover Available Commands

```bash
make help
```

## 2) Install Dependencies

```bash
make install-deps
```

## 3) Generate Protobuf Stubs

All modules:

```bash
make generate-protos
```

Single module:

```bash
make generate-protos-module MODULE=services/planning
```

Clean generated stubs:

```bash
make clean-protos
```

## 4) Run Tests

All unit suites:

```bash
make test-unit
```

Single module:

```bash
make test-module MODULE=core/shared
make test-module MODULE=services/planning
```

## 5) Run Services Locally (Examples)

Planning:

```bash
python services/planning/server.py
```

Context:

```bash
python services/context/server.py
```

Orchestrator:

```bash
python services/orchestrator/server.py
```

Workflow:

```bash
python services/workflow/server.py
```

Ray Executor:

```bash
python services/ray_executor/server.py
```

Planning UI:

```bash
cd services/planning-ui
npm ci
npm run dev
```

Note: most backend services require external dependencies (Neo4j, Valkey, NATS, Ray) and environment variables.

## 6) Deployment Shortcuts

List deployable services:

```bash
make list-services
```

Build all services:

```bash
make deploy-build          # cache
make deploy-build-no-cache # no-cache
```

Note: cached builds are the default path and automatically retry with no-cache if the cached build fails.

Deploy all services:

```bash
make deploy
# optional:
# make deploy NO_CACHE=1
# make deploy SKIP_BUILD=1
```

Deploy one service:

```bash
make deploy-service SERVICE=planning
# optional:
# make deploy-service SERVICE=planning NO_CACHE=1
# make deploy-service SERVICE=vllm-server SKIP_BUILD=1
```

Cleanup persisted messaging/storage state:

```bash
make persistence-clean
make cluster-clear
```

Prune registry tags (keep latest 2):

```bash
make service-image-prune KEEP=2
make e2e-image-prune KEEP=2
```
