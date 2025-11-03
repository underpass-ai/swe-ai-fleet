# Code Coverage Configuration - Planning Service

## Overview

The Planning Service uses **pytest-cov** for comprehensive code coverage tracking with **80% minimum threshold** for standalone development and contributes to the **90% monorepo-wide threshold** enforced by SonarCloud.

---

## Coverage Architecture

### Dual Configuration Model

The Planning Service operates in a **monorepo** with two levels of coverage configuration:

#### 1. **Service-Level Coverage** (This Directory)
- **Purpose**: Standalone development and iteration
- **Configuration**: `pyproject.toml` (this directory)
- **Threshold**: **80% minimum**
- **Scope**: `planning/` module only
- **Reports**: Local `htmlcov/`, `coverage.xml`, `coverage.json`

#### 2. **Monorepo-Level Coverage** (Root)
- **Purpose**: CI/CD and SonarCloud integration
- **Configuration**: `/pyproject.toml` (root)
- **Threshold**: **80% overall, 90% on new code** (SonarCloud)
- **Scope**: All services + core
- **Reports**: Aggregated coverage for entire fleet

---

## Quick Start

### Run Tests with Coverage (Service-Level)

```bash
# From services/planning/ directory
make test-unit              # Run unit tests with coverage
make coverage               # Comprehensive coverage analysis
make coverage-report        # Open HTML report in browser
make coverage-check         # Verify meets 80% threshold
```

### Run Tests from Monorepo Root

```bash
# From repository root
make test-unit              # Runs ALL services + core tests
# Coverage includes: core, orchestrator, monitoring, planning, context, ray_executor
```

---

## Coverage Configuration Details

### Service-Level (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=planning",           # Track planning/ module
    "--cov-branch",             # Branch coverage enabled
    "--cov-report=term-missing:skip-covered",  # Terminal output
    "--cov-report=html",        # HTML report (htmlcov/)
    "--cov-report=xml",         # XML for CI/SonarCloud
    "--cov-report=json",        # JSON for scripting
    "--cov-fail-under=80",      # 80% minimum threshold
]

[tool.coverage.run]
source = ["planning"]
branch = true                   # Track branch coverage
omit = [
    "*/tests/*",                # Exclude test files
    "*/gen/*",                  # Exclude generated gRPC code
    "*/__init__.py",            # Exclude empty __init__.py
]

[tool.coverage.report]
fail_under = 80.0               # Fail if < 80%
precision = 2                   # Show 2 decimal places
show_missing = true             # Show uncovered lines
sort = "Cover"                  # Sort by coverage %
```

### Coverage Thresholds

| Context | Line Coverage | Branch Coverage | Notes |
|---------|--------------|-----------------|-------|
| **Service Standalone** | ≥80% | ≥80% | Local development |
| **Monorepo Overall** | ≥80% | ≥80% | CI/CD gate |
| **SonarCloud New Code** | ≥90% | ≥90% | Quality gate |
| **Domain Layer** | **100%** | **100%** | ✅ Achieved! |

---

## Coverage Reports

### 1. Terminal Report

```bash
make test-unit
```

Output shows:
- Per-file coverage percentages
- Missing line numbers
- Branch coverage statistics

### 2. HTML Report

```bash
make coverage-report
```

Opens `htmlcov/index.html` showing:
- Interactive file-by-file breakdown
- Line-by-line coverage highlighting
- Branch coverage visualization
- Context switching (test → code)

### 3. XML Report (CI/SonarCloud)

```bash
make test-unit  # Generates coverage.xml
```

Used by:
- SonarCloud for quality gates
- CI/CD pipelines (GitHub Actions)
- Coverage trend tracking

### 4. JSON Report (Scripting)

```bash
make coverage  # Generates coverage.json
```

Used for:
- Automated scripts
- Coverage badges
- Custom reporting tools

---

## Current Coverage Status

### Overall

| Metric | Value |
|--------|-------|
| **Total Coverage** | **77%** |
| **Lines Covered** | ~6,600 lines |
| **Test Files** | 47 |
| **Total Tests** | 252 |

### By Layer

| Layer | Files | Tests | Coverage |
|-------|-------|-------|----------|
| **Domain** | 16 | 145 | **100%** ✅ |
| **Application** | 11 | 67 | 85% |
| **Infrastructure** | 20 | 40 | 72% |

### Improvement Plan

To reach **80% overall** (service-level threshold):

1. **Infrastructure Layer** (72% → 85%)
   - Add integration tests for Neo4j adapter
   - Test Valkey adapter edge cases
   - Test NATS adapter error handling

2. **Application Layer** (85% → 90%)
   - Test use case error paths
   - Test port contract violations
   - Test concurrent execution scenarios

**Domain layer is already at 100%** ✅ No action needed.

---

## Makefile Targets

### Testing

```bash
make test-unit              # Run unit tests (80% threshold)
make test-integration       # Run integration tests
make test                   # Alias for test-unit
```

### Coverage Analysis

```bash
make coverage               # Full coverage analysis + summary
make coverage-report        # Open HTML report
make coverage-check         # Verify threshold (CI/CD)
make coverage-summary       # Print coverage stats
```

### Cleanup

```bash
make clean                  # Remove coverage artifacts
```

---

## CI/CD Integration

### GitHub Actions Workflow

The monorepo CI runs:

```yaml
- name: Run unit tests with coverage
  run: make test-unit        # From root (all services)

- name: Fix coverage paths for SonarCloud
  run: bash scripts/fix-coverage-paths.sh

- name: SonarCloud Scan
  uses: sonarsource/sonarcloud-github-action@v3.1
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### Coverage Path Fixing

The script `scripts/fix-coverage-paths.sh`:
- Normalizes paths in `coverage.xml`
- Ensures SonarCloud can map coverage to source files
- Required for monorepo structure

---

## Best Practices

### 1. Run Tests Before Commit

```bash
# From services/planning/
make test-unit && make lint
```

### 2. Check Coverage Locally

```bash
make coverage-check
```

### 3. View Coverage Report

```bash
make coverage-report
# Opens htmlcov/index.html
```

### 4. Focus on Uncovered Code

```bash
make test-unit
# Terminal output shows "Missing" lines
```

### 5. Exclude When Necessary

Add to `pyproject.toml`:

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",        # Explicit exclusion
    "def __repr__",            # String representations
    "raise NotImplementedError",  # Abstract methods
]
```

---

## Coverage Exclusions

### Automatic Exclusions

These are **automatically excluded** from coverage:

1. **Test Files**
   - `*/tests/*`
   - `*/test_*.py`
   - `*/*_test.py`

2. **Generated Code**
   - `*/gen/*` (gRPC protobuf)
   - `*/*_pb2.py`
   - `*/*_pb2_grpc.py`
   - `*/*_pb2.pyi`

3. **Infrastructure**
   - `*/__pycache__/*`
   - `*/.venv/*`
   - `*/venv/*`

4. **Empty Files**
   - `*/__init__.py` (if empty)

### Pattern Exclusions

These **code patterns** are excluded:

```python
# Type checking blocks
if TYPE_CHECKING:
    from typing import ...

# Protocols (interfaces)
class StoragePort(Protocol):
    ...

# Abstract methods
@abstractmethod
def process(self): ...

# Debug code
if __name__ == "__main__":
    main()

# Platform-specific
if sys.platform == "win32":
    ...
```

---

## Troubleshooting

### Coverage Too Low

```bash
❌ Coverage 75% < 80% threshold
```

**Solution**:
1. Run `make coverage-report`
2. Open `htmlcov/index.html`
3. Identify files with low coverage
4. Write tests for uncovered lines

### Coverage.xml Not Generated

```bash
❌ coverage.xml not found
```

**Solution**:
```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Run tests with XML report
make test-unit
```

### Branch Coverage Low

```bash
✅ Line coverage: 85%
❌ Branch coverage: 60%
```

**Solution**: Test both branches of conditionals:

```python
# Test BOTH branches
def test_valid_input():
    # Tests: if condition is True
    result = validate(valid_input)
    assert result is True

def test_invalid_input():
    # Tests: if condition is False
    with pytest.raises(ValueError):
        validate(invalid_input)
```

### SonarCloud Path Mismatch

```bash
❌ SonarCloud shows 0% coverage
```

**Solution**:
```bash
# Run from root
bash scripts/fix-coverage-paths.sh
cat coverage.xml  # Verify paths are correct
```

---

## Architecture Compliance

### DDD + Hexagonal Architecture

Coverage configuration respects architectural boundaries:

1. **Domain Layer**
   - **100% coverage required**
   - Pure business logic
   - No infrastructure dependencies

2. **Application Layer**
   - **85%+ coverage target**
   - Use case orchestration
   - Mocked port dependencies

3. **Infrastructure Layer**
   - **75%+ coverage target**
   - Adapter implementations
   - Integration tests preferred

### Testing Strategy

```
Domain Tests → Unit tests (fast, comprehensive)
Application Tests → Unit tests with mocked ports
Infrastructure Tests → Integration tests (slower)
```

---

## Related Documentation

- **Testing Strategy**: `/docs/TESTING_ARCHITECTURE.md`
- **SonarCloud Config**: `/sonar-project.properties`
- **CI/CD Pipeline**: `/.github/workflows/ci.yml`
- **Architecture**: `ARCHITECTURE.md` (this directory)
- **Hexagonal Principles**: `/docs/HEXAGONAL_ARCHITECTURE_PRINCIPLES.md`

---

## References

- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [SonarCloud Coverage](https://docs.sonarcloud.io/enriching/test-coverage/overview/)

---

**Coverage is not just a metric—it's a safety net for refactoring and a signal of code quality.**

Maintain **80%+ coverage** to ensure the Planning Service remains maintainable, testable, and production-ready.

