# Testing Scripts

Organized testing scripts for SWE AI Fleet project.

## 📁 Structure

```
scripts/test/
├── unit.sh         # Unit tests (fast, no external deps)
├── integration.sh  # Integration tests (Podman containers)
├── e2e.sh          # End-to-end tests (full system)
├── coverage.sh     # Unit tests with coverage report
├── all.sh          # Run all test suites
└── README.md       # This file
```

## 🚀 Usage

### Unit Tests (Recommended for development)

```bash
# Run all unit tests
./scripts/test/unit.sh

# Run specific test file
./scripts/test/unit.sh services/orchestrator/tests/domain/test_agent_config.py

# Run with verbose output
./scripts/test/unit.sh -v
```

### Coverage Report

```bash
# Run tests with coverage (for CI/SonarQube)
./scripts/test/coverage.sh

# View HTML coverage report
open htmlcov/index.html
```

### Integration Tests

```bash
# Run integration tests with Podman
./scripts/test/integration.sh
```

**Requirements:**
- Podman installed and running
- Podman socket active: `systemctl --user start podman.socket`

### E2E Tests

```bash
# Run end-to-end tests
./scripts/test/e2e.sh
```

**Requirements:**
- Full cluster deployed (Kubernetes/local)
- All services running

### All Tests

```bash
# Run complete test suite (unit → integration → e2e)
./scripts/test/all.sh
```

## 📊 Test Markers

Tests are organized with pytest markers:

- `pytest -m "not e2e and not integration"` - Unit tests only (fast)
- `pytest -m integration` - Integration tests
- `pytest -m e2e` - E2E tests

## 🎯 CI/CD Usage

For CI pipelines, use:

```bash
# CI with coverage (SonarQube)
./scripts/test/coverage.sh

# Or use the existing CI script
./scripts/ci-test-with-grpc-gen.sh
```

## 📝 Specific Service Tests

### Context Service Persistence

For Context service persistence tests (Neo4j + Redis):

```bash
cd tests/integration/services/context
./run-persistence-test.sh
```

## ✅ Test Requirements

### Unit Tests
- Python 3.13+
- Virtual environment activated
- Dependencies installed: `pip install -e '.[grpc,dev]'`

### Integration Tests
- Podman installed
- Podman socket running
- Container images built

### E2E Tests
- Kubernetes cluster or local deployment
- All services deployed
- Network connectivity

## 🔧 Troubleshooting

### Protobuf generation fails

```bash
# Install grpcio-tools
pip install grpcio-tools

# Or regenerate manually
python -m grpc_tools.protoc --proto_path=specs ...
```

### Coverage below 90%

Check which files need more tests:

```bash
./scripts/test/coverage.sh
# Review coverage.xml or htmlcov/index.html
```

### Podman tests fail

```bash
# Check Podman is running
podman version

# Start Podman socket
systemctl --user start podman.socket

# Check socket
echo $DOCKER_HOST  # Should be unix:///run/user/$(id -u)/podman/podman.sock
```

