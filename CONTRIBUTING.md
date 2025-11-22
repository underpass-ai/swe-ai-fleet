# Contributing to SWE AI Fleet

Thank you for your interest in contributing! We are building the industry reference architecture for autonomous software engineering.

## 🛠️ Development Standards

We strictly enforce **Domain-Driven Design (DDD)** and **Hexagonal Architecture**. Before writing code, please read:

1.  **[Hexagonal Architecture Principles](docs/normative/HEXAGONAL_ARCHITECTURE.md)** (Must Read)
2.  **[Testing Architecture](docs/TESTING_ARCHITECTURE.md)** (Mandatory)

### Key Rules
-   **No Domain Dependencies**: The `domain/` folder must never import from `infrastructure/`.
-   **Immutable Entities**: Use `@dataclass(frozen=True)` for all domain entities.
-   **Fail Fast**: Validate inputs in `__post_init__`.
-   **English Only**: Code, comments, and commit messages must be in English.

## 💻 Local Development Setup

We recommend using **Podman** and a Python virtual environment.

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies & tools
pip install -e .
pip install ruff pre-commit

# 3. Install pre-commit hooks
pre-commit install
```

## 🧪 Testing

We have a high bar for quality. All PRs must include tests.

```bash
# Run unit tests
pytest services/<service>/tests/unit

# Run linting
ruff check .
```

## 📨 Pull Request Process

1.  **Fork & Branch**: Create a feature branch from `main`.
2.  **Implement**: Write code + tests.
3.  **Lint**: Ensure `ruff check` passes.
4.  **Open PR**: distinct, descriptive title. Link to any related issues.

## 🧩 Directory Structure

-   `core/`: Shared domain logic and libraries.
-   `services/`: Deployable microservices.
-   `deploy/`: Infrastructure configuration.
-   `docs/`: Documentation (See [Documentation Map](docs/README.md)).

---

## ❓ Questions?

Check the [README](README.md) or open an issue on GitHub.
