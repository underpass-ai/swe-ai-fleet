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

Deploy all services:

```bash
make fresh-redeploy
# or
make fast-redeploy
```

Deploy one service:

```bash
make deploy-service SERVICE=planning
# or
make deploy-service-fast SERVICE=planning
```

Cleanup persisted messaging/storage state:

```bash
make persistence-clean
```
