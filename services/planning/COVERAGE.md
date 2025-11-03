# Code Coverage Configuration - Planning Service

## Overview

The Planning Service uses **pytest-cov** for comprehensive code coverage tracking. Coverage **quality gates are enforced by SonarCloud**, not locally:

- **SonarCloud Overall**: ≥70% minimum (`sonar.coverage.minimum`)
- **SonarCloud New Code**: ≥80% minimum (`sonar.newCode.coverage.minimum`)

Local coverage reports are **informative** to help developers identify untested code during development.

---

## Coverage Architecture

### Dual Configuration Model

The Planning Service operates in a **monorepo** with two levels of coverage configuration:

#### 1. **Service-Level Coverage** (This Directory)
- **Purpose**: Standalone development and iteration
- **Configuration**: `pyproject.toml` (this directory)
- **Threshold**: None locally (informative only)
- **Scope**: `planning/` module only
- **Reports**: Local `htmlcov/`, `coverage.xml`, `coverage.json`

#### 2. **Monorepo-Level Coverage** (Root)
- **Purpose**: CI/CD and SonarCloud integration
- **Configuration**: `/pyproject.toml` (root)
- **Quality Gates**: **SonarCloud enforces thresholds**
  - Overall: ≥70% (`sonar.coverage.minimum`)
  - New code: ≥80% (`sonar.newCode.coverage.minimum`)
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
make coverage-check         # Display coverage report + SonarCloud thresholds
```

### Run Tests from Monorepo Root

```bash
# From repository root
make test-unit              # Runs ALL services + core tests
# Coverage includes: core, orchestrator, monitoring, planning, context, ray_executor

# Tests run SEQUENTIALLY per service to avoid pytest namespace collisions
# Each service has its own conftest.py and test isolation
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

| Context | Line Coverage | Branch Coverage | Enforced By |
|---------|--------------|-----------------|-------------|
| **Local Development** | Informative only | Informative only | None (developer feedback) |
| **SonarCloud Overall** | ≥70% | ≥70% | **Quality Gate** 🚦 |
| **SonarCloud New Code** | ≥80% | ≥80% | **Quality Gate** 🚦 |
| **Domain Layer (Target)** | **100%** | **100%** | ✅ Achieved! |

**Note**: Local pytest does NOT fail on low coverage. SonarCloud is the single source of truth for quality gates.

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

### 3. XML Report (CI/SonarCloud) 🚦

```bash
make test-unit  # Generates coverage.xml
```

**This is the authoritative report** used by:
- **SonarCloud quality gates** (70% overall, 80% new code)
- CI/CD pipelines (GitHub Actions)
- Coverage trend tracking
- PR approval/rejection decisions

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

To maintain **SonarCloud quality gates** (70% overall minimum):

**Current Status**: 77% overall ✅ (meets SonarCloud 70% threshold)

**Target for Excellence** (80%+ overall):

1. **Infrastructure Layer** (72% → 85%)
   - Add integration tests for Neo4j adapter
   - Test Valkey adapter edge cases
   - Test NATS adapter error handling

2. **Application Layer** (85% → 90%)
   - Test use case error paths
   - Test port contract violations
   - Test concurrent execution scenarios

**Domain layer is already at 100%** ✅ No action needed.

**Note**: New code must maintain ≥80% coverage (SonarCloud quality gate).

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

### ImportPathMismatchError (Monorepo Pytest Collision)

```bash
ImportPathMismatchError: ('tests.conftest', ...)
```

**Cause**: Multiple services have `tests/conftest.py` files. When pytest discovers all tests at once, it tries to import them all as `tests.conftest`, causing a namespace collision.

**Solution**: The monorepo test script (`scripts/test/unit.sh`) runs each service's tests **sequentially** with `--cov-append` to avoid this issue:

```bash
# Run each service independently
pytest --cov=services/orchestrator services/orchestrator/tests/
pytest --cov=services/planning --cov-append services/planning/tests/
# etc.
```

**Root Cause Fixed**:
- Root `pyproject.toml` now only has `testpaths = ["tests"]` (core tests only)
- Service tests are run separately by the CI script
- Each run appends to the same coverage data file
- Final reports combine all coverage

### SonarCloud Quality Gate Fails

```bash
❌ SonarCloud: Coverage 65% < 70% minimum
❌ SonarCloud: New code coverage 75% < 80% minimum
```

**Solution**:
1. Check SonarCloud dashboard for specific files
2. Run `make coverage-report` locally
3. Open `htmlcov/index.html`
4. Identify files with low coverage
5. Write tests for uncovered lines
6. Focus on **new code** first (80% requirement)

**Note**: Local pytest will NOT fail - only SonarCloud enforces thresholds.

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

**SonarCloud Quality Gates** ensure code meets production standards:
- ✅ **70% overall coverage minimum** - Ensures existing code is tested
- ✅ **80% new code coverage minimum** - Maintains high quality for new features

Local coverage reports help developers **identify gaps early** before CI/CD runs.

